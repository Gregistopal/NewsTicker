import asyncio
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from aiohttp.test_utils import TestClient, TestServer


SERVER_PATH = Path(__file__).parents[1] / "app" / "server.py"
SPEC = importlib.util.spec_from_file_location("news_ticker_server", SERVER_PATH)
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class SettingsTests(unittest.TestCase):
    def test_normalization_clamps_values_and_sanitizes_messages(self):
        result = server.normalize_settings({
            "intervalSeconds": -50,
            "visibleSeconds": 9999,
            "tickerOpacity": 0,
            "command": "news extra",
            "tickerText": "not-a-color",
            "messages": [
                {"id": "same", "text": "  First\nheadline  ", "enabled": True},
                {"id": "same", "text": "Second", "enabled": False},
                {"text": ""},
            ],
        })
        self.assertEqual(result["intervalSeconds"], 5)
        self.assertEqual(result["visibleSeconds"], 300)
        self.assertEqual(result["tickerOpacity"], 0.35)
        self.assertEqual(result["command"], "!news")
        self.assertEqual(result["tickerText"], server.DEFAULT["tickerText"])
        self.assertEqual(result["messages"][0]["text"], "First headline")
        self.assertNotEqual(result["messages"][0]["id"], result["messages"][1]["id"])

    def test_command_parsing_is_exact_and_case_insensitive(self):
        self.assertEqual(server.parse_command({"text": "!NEWS 2"}, "!news"), "2")
        self.assertEqual(server.parse_command({"message": "!news urgent update"}, "!news"), "urgent update")
        self.assertIsNone(server.parse_command({"text": "!newsletter"}, "!news"))

    def test_moderator_detection_supports_role_and_badges(self):
        self.assertTrue(server.is_moderator({"user": {"role": 3}}))
        self.assertTrue(server.is_moderator({"user": {"role": 4}}))
        self.assertTrue(server.is_moderator({"user": {"badges": [{"name": "moderator"}]}}))
        self.assertFalse(server.is_moderator({"user": {"role": 2}}))


class AppTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.old_data_root = server.DATA_ROOT
        self.temp = tempfile.TemporaryDirectory()
        server.DATA_ROOT = Path(self.temp.name)
        self.ticker = server.NewsTicker(port_override=18999, no_browser=True)
        self.http = TestClient(TestServer(self.ticker.make_app()))
        await self.http.start_server()

    async def asyncTearDown(self):
        await self.http.close()
        self.temp.cleanup()
        server.DATA_ROOT = self.old_data_root

    async def test_state_redacts_password_and_exposes_token(self):
        self.ticker.config["streamerPassword"] = "secret"
        response = await self.http.get("/api/state")
        self.assertEqual(response.status, 200)
        data = await response.json()
        self.assertNotIn("streamerPassword", data["settings"])
        self.assertTrue(data["settings"]["hasStreamerPassword"])
        self.assertEqual(data["csrfToken"], self.ticker.csrf)

    async def test_control_requests_require_token(self):
        response = await self.http.post("/api/show", json={})
        self.assertEqual(response.status, 403)

    async def test_show_and_hide_lifecycle(self):
        headers = {"X-NewsTicker-Token": self.ticker.csrf}
        response = await self.http.post("/api/show", json={}, headers=headers)
        self.assertEqual(response.status, 200)
        shown = await response.json()
        self.assertIsNotNone(shown["active"])
        response = await self.http.post("/api/hide", json={}, headers=headers)
        hidden = await response.json()
        self.assertIsNone(hidden["active"])
        self.assertIsNotNone(hidden["nextAutoAt"])

    async def test_moderator_command_custom_and_saved_number(self):
        self.ticker.config["command"] = "!news"
        self.ticker.config["commandEnabled"] = True
        await self.ticker.handle_streamer_event({
            "event": {"source": "Twitch", "type": "ChatMessage"},
            "data": {"text": "!news Custom alert", "user": {"name": "Mod", "role": 3}},
        })
        self.assertEqual(self.ticker.active["text"], "Custom alert")
        await self.ticker.handle_streamer_event({
            "event": {"source": "Twitch", "type": "ChatMessage"},
            "data": {"text": "!news 2", "user": {"name": "Owner", "role": 4}},
        })
        self.assertEqual(self.ticker.active["text"], server.DEFAULT_MESSAGES[1]["text"])

    async def test_viewer_command_is_rejected(self):
        await self.ticker.handle_streamer_event({
            "event": {"source": "Twitch", "type": "ChatMessage"},
            "data": {"text": "!news Fake alert", "user": {"name": "Viewer", "role": 1}},
        })
        self.assertIsNone(self.ticker.active)
        self.assertEqual(self.ticker.status["deniedCommands"], 1)


if __name__ == "__main__":
    unittest.main()
