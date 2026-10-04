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
            "itemsPerAppearance": 99,
            "counterFlipSeconds": 0,
            "daysLiveStartDate": "not-a-date",
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
        self.assertEqual(result["itemsPerAppearance"], 20)
        self.assertEqual(result["counterFlipSeconds"], 2)
        self.assertEqual(result["daysLiveStartDate"], server.DEFAULT["daysLiveStartDate"])
        self.assertEqual(result["tickerOpacity"], 0.35)
        self.assertEqual(result["command"], "!news")
        self.assertEqual(result["tickerText"], server.DEFAULT["tickerText"])
        self.assertEqual(result["messageMode"], "crawl")
        self.assertNotIn("showKicker", result)
        self.assertEqual(result["tickerHeight"], 72)
        self.assertEqual(result["layoutVersion"], 4)
        self.assertEqual(result["bottomOffset"], 0)
        self.assertEqual(result["sideMargin"], 0)
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

    def test_days_live_parser_is_inclusive(self):
        self.assertEqual(server.parse_start_date("9/25/2026"), "2026-09-25")
        self.assertEqual(server.days_live_count(server.date.today().isoformat()), 1)
        self.assertIsNone(server.parse_start_date("tomorrow-ish"))


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

    async def test_web_assets_disable_stale_browser_caching(self):
        for path in ("/", "/overlay", "/static/overlay.js", "/static/control.js"):
            response = await self.http.get(path)
            self.assertEqual(response.status, 200)
            self.assertIn("no-store", response.headers.get("Cache-Control", ""))

    async def test_v101_layout_migrates_to_compact_ticker(self):
        legacy = dict(server.DEFAULT)
        legacy.update({"layoutVersion": 2, "tickerHeight": 92, "showKicker": True})
        self.ticker.settings_path.write_text(json.dumps(legacy), encoding="utf-8")
        migrated = server.NewsTicker(port_override=18998, no_browser=True)
        self.assertEqual(migrated.config["layoutVersion"], 4)
        self.assertEqual(migrated.config["tickerHeight"], 72)
        self.assertNotIn("showKicker", migrated.config)

    async def test_control_requests_require_token(self):
        response = await self.http.post("/api/show", json={})
        self.assertEqual(response.status, 403)

    async def test_show_and_hide_lifecycle(self):
        headers = {"X-NewsTicker-Token": self.ticker.csrf}
        response = await self.http.post("/api/show", json={}, headers=headers)
        self.assertEqual(response.status, 200)
        shown = await response.json()
        self.assertIsNotNone(shown["active"])
        self.assertEqual(shown["active"]["minimumItems"], 2)
        self.assertEqual(shown["active"]["minimumHideAt"], 0)
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

    async def test_one_off_replays_entrance_then_resumes_regular_items(self):
        await self.ticker.show_next("automatic")
        original_id = self.ticker.active["id"]
        await self.ticker.show_one_off("Priority alert", "moderator command", "Mod")
        self.assertIsNone(self.ticker.active)
        self.assertIsNotNone(self.ticker.transition_at)
        await self.ticker.start_next_priority()
        self.assertNotEqual(self.ticker.active["id"], original_id)
        self.assertTrue(self.ticker.active["priority"])
        self.assertEqual(self.ticker.active["items"][0]["text"], "Priority alert")
        self.assertTrue(self.ticker.active["items"][0]["priority"])
        self.assertTrue(any(not item["priority"] for item in self.ticker.active["items"][1:]))
        self.assertEqual(self.ticker.active["minimumItems"], 3)
        self.assertEqual(self.ticker.active["loopStart"], 1)

    async def test_completion_waits_for_full_minimum_at_message_boundary(self):
        await self.ticker.show_next("automatic")
        active_id = self.ticker.active["id"]
        self.ticker.active["minimumHideAt"] = server.now_ms() - 1
        completed = await self.ticker.complete_active_at_boundary(active_id, 1)
        self.assertFalse(completed)
        self.assertIsNotNone(self.ticker.active)
        completed = await self.ticker.complete_active_at_boundary(active_id, 2)
        self.assertTrue(completed)
        self.assertIsNone(self.ticker.active)

    async def test_random_bag_plays_every_message_before_repeating(self):
        class ReverseRandomizer:
            @staticmethod
            def shuffle(values):
                values.reverse()

        self.ticker.randomizer = ReverseRandomizer()
        self.ticker.config["messages"] = [
            {"id": str(index), "text": f"Headline {index}", "enabled": True}
            for index in range(1, 6)
        ]
        self.ticker.config["itemsPerAppearance"] = 2
        first = self.ticker.next_regular_sequence()
        second = self.ticker.next_regular_sequence()
        third = self.ticker.next_regular_sequence()
        played = [item["messageId"] for item in first + second + third]
        self.assertEqual(len(set(played[:5])), 5)
        self.assertNotEqual(played[:2], ["1", "2"])
        self.assertNotEqual(played[4], played[5])

    async def test_overlay_websocket_can_close_at_a_message_boundary(self):
        websocket = await self.http.ws_connect("/ws")
        await websocket.receive_json()
        await self.ticker.show_next("automatic")
        active_state = await websocket.receive_json()
        active_id = active_state["active"]["id"]
        self.ticker.active["minimumHideAt"] = server.now_ms() - 1
        await websocket.send_json({
            "type": "sequenceComplete",
            "activeId": active_id,
            "completedItems": 2,
        })
        hidden_state = await websocket.receive_json()
        self.assertIsNone(hidden_state["active"])
        await websocket.close()

    async def test_chat_management_commands_persist_and_reply(self):
        class Socket:
            closed = False

            def __init__(self):
                self.sent = []

            async def send_json(self, packet):
                self.sent.append(packet)

        socket = Socket()
        self.ticker.streamer_socket = socket
        self.ticker.streamer_chat_ready = True
        event = lambda text: {
            "event": {"source": "Twitch", "type": "ChatMessage"},
            "data": {"text": text, "user": {"name": "Mod", "role": 3}},
        }

        await self.ticker.handle_streamer_event(event("!news add New persistent item"))
        self.assertEqual(self.ticker.config["messages"][-1]["text"], "New persistent item")
        saved = json.loads(self.ticker.settings_path.read_text("utf-8"))
        self.assertEqual(saved["messages"][-1]["text"], "New persistent item")
        self.assertEqual(socket.sent[-1]["request"], "SendMessage")
        self.assertFalse(socket.sent[-1]["bot"])
        self.assertIn("added item", socket.sent[-1]["message"])

        reply_id = socket.sent[-1]["id"]
        self.assertIn(reply_id, self.ticker.pending_chat_requests)
        await self.ticker.handle_chat_response({"id": reply_id, "status": "ok"})
        self.assertEqual(self.ticker.status["chatReplies"], "ready")
        self.assertIn("broadcaster", self.ticker.status["chatReplyDetail"])

        await self.ticker.handle_streamer_event(event("!news list"))
        self.assertIn("New persistent item", socket.sent[-1]["message"])
        await self.ticker.handle_streamer_event(event("!news help"))
        self.assertIn("!news delete", socket.sent[-1]["message"])
        self.assertIn("!news days", socket.sent[-1]["message"])

        await self.ticker.handle_streamer_event(event("!news days 2025-01-15"))
        self.assertEqual(self.ticker.config["daysLiveStartDate"], "2025-01-15")
        saved = json.loads(self.ticker.settings_path.read_text("utf-8"))
        self.assertEqual(saved["daysLiveStartDate"], "2025-01-15")
        self.assertIn("start date set", socket.sent[-1]["message"])

        await self.ticker.handle_streamer_event(event("!news delete 4"))
        self.assertEqual(len(self.ticker.config["messages"]), 3)
        self.assertIn("deleted item 4", socket.sent[-1]["message"])

    async def test_viewer_command_is_rejected(self):
        await self.ticker.handle_streamer_event({
            "event": {"source": "Twitch", "type": "ChatMessage"},
            "data": {"text": "!news Fake alert", "user": {"name": "Viewer", "role": 1}},
        })
        self.assertIsNone(self.ticker.active)
        self.assertEqual(self.ticker.status["deniedCommands"], 1)


if __name__ == "__main__":
    unittest.main()
