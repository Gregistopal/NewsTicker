"""NewsTicker portable local companion for OBS and Streamer.bot."""

from __future__ import annotations

import argparse
import asyncio
import base64
from collections import deque
import contextlib
import ctypes
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import secrets
import sys
import time
from urllib.request import urlopen
import uuid
import webbrowser

from aiohttp import ClientSession, ClientTimeout, WSMsgType, web


VERSION = "1.0.1"
ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = Path(__file__).resolve().parent / "web"
DATA_ROOT = ROOT / "data"

FONT_CHOICES = {
    "Segoe UI": "'Segoe UI', Arial, sans-serif",
    "Arial": "Arial, Helvetica, sans-serif",
    "Verdana": "Verdana, Geneva, sans-serif",
    "Trebuchet MS": "'Trebuchet MS', Arial, sans-serif",
    "Tahoma": "Tahoma, Verdana, sans-serif",
    "Georgia": "Georgia, 'Times New Roman', serif",
    "Courier New": "'Courier New', monospace",
    "Impact": "Impact, Haettenschweiler, sans-serif",
}

DEFAULT_MESSAGES = [
    {"id": "welcome", "text": "Welcome to the stream — thanks for watching!", "enabled": True},
    {"id": "follow", "text": "Follow the channel so you never miss the next broadcast.", "enabled": True},
    {"id": "socials", "text": "Check the channel panels for community links and stream information.", "enabled": True},
]

DEFAULT = {
    "layoutVersion": 2,
    "serverPort": 18770,
    "autoEnabled": True,
    "intervalSeconds": 90,
    "visibleSeconds": 12,
    "commandEnabled": True,
    "command": "!news",
    "allowCustomCommandText": True,
    "streamerUrl": "ws://127.0.0.1:8080/",
    "streamerPassword": "",
    "breakingLabel": "BREAKING NEWS",
    "kickerText": "LIVE UPDATE",
    "showKicker": True,
    "showClock": True,
    "clock24Hour": False,
    "fontFamily": "Segoe UI",
    "fontSize": 38,
    "fontWeight": 700,
    "messageMode": "crawl",
    "crawlSpeed": 150,
    "uppercaseMessage": False,
    "tickerHeight": 92,
    "labelWidth": 292,
    "bottomOffset": 0,
    "sideMargin": 0,
    "cornerRadius": 0,
    "tickerOpacity": 0.97,
    "shadowStrength": 0.42,
    "enterMs": 850,
    "exitMs": 500,
    "shineEnabled": True,
    "breakingBackground": "#d71920",
    "breakingText": "#ffffff",
    "tickerBackground": "#091421",
    "tickerText": "#f8fbff",
    "accentColor": "#ffd447",
    "mutedText": "#afbac8",
    "messages": DEFAULT_MESSAGES,
}


def now_ms() -> int:
    return int(time.time() * 1000)


def clamp_number(value, low, high, default, integer=False):
    try:
        result = float(value)
        if result != result or result in (float("inf"), float("-inf")):
            raise ValueError
    except (TypeError, ValueError):
        result = float(default)
    result = max(low, min(high, result))
    return int(round(result)) if integer else result


def clean_color(value, default):
    value = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value.lower()
    return default


def clean_text(value, maximum, default=""):
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value or ""))
    value = re.sub(r"\s+", " ", value).strip()
    return value[:maximum] or default


def normalize_command(value):
    command = clean_text(value, 40, "!news").split()[0]
    if not command.startswith("!"):
        command = "!" + command
    return command.lower()


def normalize_settings(raw, previous=None):
    previous = previous or DEFAULT
    result = dict(DEFAULT)
    result.update({k: v for k, v in previous.items() if k in DEFAULT})

    boolean_keys = (
        "autoEnabled", "commandEnabled", "allowCustomCommandText", "showKicker",
        "showClock", "clock24Hour", "uppercaseMessage", "shineEnabled",
    )
    for key in boolean_keys:
        if key in raw:
            result[key] = bool(raw[key])

    result["serverPort"] = clamp_number(raw.get("serverPort", result["serverPort"]), 1024, 65535, 18770, True)
    result["intervalSeconds"] = clamp_number(raw.get("intervalSeconds", result["intervalSeconds"]), 5, 86400, 90, True)
    result["visibleSeconds"] = clamp_number(raw.get("visibleSeconds", result["visibleSeconds"]), 3, 300, 12, True)
    result["fontSize"] = clamp_number(raw.get("fontSize", result["fontSize"]), 20, 72, 38, True)
    result["fontWeight"] = clamp_number(raw.get("fontWeight", result["fontWeight"]), 400, 900, 700, True)
    result["crawlSpeed"] = clamp_number(raw.get("crawlSpeed", result["crawlSpeed"]), 40, 500, 150, True)
    result["tickerHeight"] = clamp_number(raw.get("tickerHeight", result["tickerHeight"]), 64, 150, 92, True)
    result["labelWidth"] = clamp_number(raw.get("labelWidth", result["labelWidth"]), 190, 420, 292, True)
    result["bottomOffset"] = clamp_number(raw.get("bottomOffset", result["bottomOffset"]), 0, 260, 0, True)
    result["sideMargin"] = clamp_number(raw.get("sideMargin", result["sideMargin"]), 0, 260, 0, True)
    result["cornerRadius"] = clamp_number(raw.get("cornerRadius", result["cornerRadius"]), 0, 28, 0, True)
    result["tickerOpacity"] = clamp_number(raw.get("tickerOpacity", result["tickerOpacity"]), 0.35, 1, 0.97)
    result["shadowStrength"] = clamp_number(raw.get("shadowStrength", result["shadowStrength"]), 0, 1, 0.42)
    result["enterMs"] = clamp_number(raw.get("enterMs", result["enterMs"]), 250, 2000, 850, True)
    result["exitMs"] = clamp_number(raw.get("exitMs", result["exitMs"]), 200, 1500, 500, True)

    result["command"] = normalize_command(raw.get("command", result["command"]))
    result["streamerUrl"] = clean_text(raw.get("streamerUrl", result["streamerUrl"]), 300, "ws://127.0.0.1:8080/")
    if not result["streamerUrl"].lower().startswith(("ws://", "wss://")):
        result["streamerUrl"] = "ws://127.0.0.1:8080/"
    if "streamerPassword" in raw:
        result["streamerPassword"] = str(raw.get("streamerPassword") or "")[:300]
    result["breakingLabel"] = clean_text(raw.get("breakingLabel", result["breakingLabel"]), 32, "BREAKING NEWS")
    result["kickerText"] = clean_text(raw.get("kickerText", result["kickerText"]), 32, "LIVE UPDATE")
    result["fontFamily"] = raw.get("fontFamily") if raw.get("fontFamily") in FONT_CHOICES else result["fontFamily"]
    # Version 1.0.1 is a true news crawl. Keeping this server-side prevents an
    # older saved 1.0.0 "headline" value from restoring the clipped static text.
    result["messageMode"] = "crawl"
    result["layoutVersion"] = 2

    for key in ("breakingBackground", "breakingText", "tickerBackground", "tickerText", "accentColor", "mutedText"):
        result[key] = clean_color(raw.get(key, result[key]), DEFAULT[key])

    source_messages = raw.get("messages", result["messages"])
    messages = []
    seen_ids = set()
    if isinstance(source_messages, list):
        for item in source_messages[:100]:
            if not isinstance(item, dict):
                continue
            text = clean_text(item.get("text"), 320)
            if not text:
                continue
            identifier = clean_text(item.get("id"), 80) or uuid.uuid4().hex
            if identifier in seen_ids:
                identifier = uuid.uuid4().hex
            seen_ids.add(identifier)
            messages.append({"id": identifier, "text": text, "enabled": bool(item.get("enabled", True))})
    result["messages"] = messages
    return result


def is_moderator(data):
    user = data.get("user") if isinstance(data.get("user"), dict) else {}
    role = user.get("role", data.get("role", 0))
    try:
        if int(role) >= 3:  # Streamer.bot: 3 moderator, 4 broadcaster.
            return True
    except (TypeError, ValueError):
        pass
    user_type = str(user.get("type", data.get("userType", ""))).lower()
    if user_type in ("moderator", "broadcaster", "mod"):
        return True
    badges = user.get("badges") or data.get("badges") or []
    for badge in badges:
        name = badge.get("name", "") if isinstance(badge, dict) else str(badge)
        if str(name).lower() in ("moderator", "broadcaster"):
            return True
    return False


def event_text(data):
    value = data.get("text", data.get("message", ""))
    if isinstance(value, dict):
        value = value.get("message", value.get("text", ""))
    return clean_text(value, 1000)


def parse_command(data, command):
    text = event_text(data)
    if not text:
        return None
    first, separator, rest = text.partition(" ")
    if first.lower() != command.lower():
        return None
    return rest.strip() if separator else ""


def atomic_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


class NewsTicker:
    def __init__(self, port_override=None, no_browser=False):
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
        (DATA_ROOT / "backups").mkdir(exist_ok=True)
        self.settings_path = DATA_ROOT / "settings.json"
        self.config = dict(DEFAULT)
        self.config["messages"] = [dict(item) for item in DEFAULT_MESSAGES]
        if self.settings_path.exists():
            try:
                saved = json.loads(self.settings_path.read_text("utf-8"))
                if "layoutVersion" not in saved:
                    # One-time migration from the inset 1.0.0 lower third.
                    saved.update({
                        "layoutVersion": 2,
                        "messageMode": "crawl",
                        "bottomOffset": 0,
                        "sideMargin": 0,
                        "cornerRadius": 0,
                    })
                self.config = normalize_settings(saved, self.config)
            except (OSError, ValueError, TypeError):
                logging.exception("Settings could not be loaded; defaults are in use")
        self.port = int(port_override or self.config["serverPort"])
        self.no_browser = no_browser
        self.clients = set()
        self.active = None
        self.cursor = -1
        self.priority_queue = deque()
        self.transition_at = None
        self.streamer_socket = None
        self.streamer_chat_ready = False
        self.next_auto_at = now_ms() + self.config["intervalSeconds"] * 1000 if self.config["autoEnabled"] else None
        self.status = {
            "streamer": "disconnected",
            "streamerDetail": "Waiting to connect",
            "chatReplies": "unavailable",
            "chatReplyDetail": "Waiting for Streamer.bot",
            "lastTrigger": None,
            "lastTriggerBy": None,
            "deniedCommands": 0,
        }
        self.csrf = secrets.token_urlsafe(24)
        self.restart_streamer = asyncio.Event()
        self.shutdown = asyncio.Event()
        self.tasks = []

    def public_settings(self):
        value = dict(self.config)
        value["fontStack"] = FONT_CHOICES[value["fontFamily"]]
        value.pop("streamerPassword", None)
        value["hasStreamerPassword"] = bool(self.config.get("streamerPassword"))
        return value

    def snapshot(self, include_token=False):
        result = {
            "type": "state",
            "version": VERSION,
            "serverTime": now_ms(),
            "settings": self.public_settings(),
            "status": dict(self.status),
            "active": dict(self.active) if self.active else None,
            "priorityQueued": len(self.priority_queue),
            "nextAutoAt": self.next_auto_at,
            "overlayUrl": f"http://127.0.0.1:{self.port}/overlay",
            "controlUrl": f"http://127.0.0.1:{self.port}/",
        }
        if include_token:
            result["csrfToken"] = self.csrf
        return result

    async def publish(self):
        packet = self.snapshot()
        for client in list(self.clients):
            try:
                await asyncio.wait_for(client.send_json(packet), timeout=0.4)
            except (Exception, asyncio.TimeoutError):
                self.clients.discard(client)
                with contextlib.suppress(Exception):
                    await client.close()

    async def persist_config(self):
        self.backup_settings()
        atomic_json(self.settings_path, self.config)
        await self.publish()

    def enabled_messages(self):
        return [item for item in self.config["messages"] if item.get("enabled") and item.get("text")]

    def message_by_position(self, position):
        messages = self.config["messages"]
        if not messages:
            return None
        if 1 <= position <= len(messages):
            return messages[position - 1]
        return None

    def next_regular_sequence(self):
        enabled = self.enabled_messages()
        if not enabled:
            return []
        self.cursor = (self.cursor + 1) % len(enabled)
        ordered = enabled[self.cursor:] + enabled[:self.cursor]
        return [
            {"messageId": item["id"], "text": item["text"], "priority": False}
            for item in ordered
        ]

    def estimated_crawl_ms(self, text):
        # The browser performs the exact pixel measurement. This conservative
        # server estimate prevents a session from closing before its first
        # crawl (or a priority alert plus its first regular item) can finish.
        clock_width = 150 if self.config.get("showClock") else 0
        viewport = max(
            420,
            1920 - self.config["labelWidth"] - self.config["sideMargin"] * 2 - clock_width - 80,
        )
        estimated_text_width = max(120, len(text) * self.config["fontSize"] * 0.56)
        distance = viewport + estimated_text_width + 48
        return max(3000, int(distance / self.config["crawlSpeed"] * 1000))

    async def show_next(self, source="manual", triggered_by=None):
        items = self.next_regular_sequence()
        if not items:
            return False
        first = items[0]
        await self.show(
            first["text"], first["messageId"], source, triggered_by, items=items
        )
        return True

    async def show(self, text, message_id=None, source="manual", triggered_by=None, priority=False, items=None):
        text = clean_text(text, 320)
        if not text:
            return False
        items = items or [{"messageId": message_id, "text": text, "priority": bool(priority)}]
        clean_items = []
        for item in items[:100]:
            item_text = clean_text(item.get("text"), 320) if isinstance(item, dict) else ""
            if item_text:
                clean_items.append({
                    "messageId": item.get("messageId"),
                    "text": item_text,
                    "priority": bool(item.get("priority")),
                })
        if not clean_items:
            return False
        start = now_ms() + 120
        base_duration = self.config["visibleSeconds"] * 1000
        required = [clean_items[0]]
        if priority:
            required = [item for item in clean_items if item["priority"]]
            first_regular = next((item for item in clean_items if not item["priority"]), None)
            if first_regular:
                required.append(first_regular)
        crawl_budget = sum(self.estimated_crawl_ms(item["text"]) for item in required)
        duration = max(base_duration, self.config["enterMs"] + crawl_budget + 250)
        self.active = {
            "id": uuid.uuid4().hex,
            "messageId": message_id,
            "text": text,
            "items": clean_items,
            "source": source,
            "priority": bool(priority),
            "triggeredBy": clean_text(triggered_by, 80) if triggered_by else None,
            "startAt": start,
            "hideAt": start + duration,
        }
        self.status["lastTrigger"] = now_ms()
        self.status["lastTriggerBy"] = triggered_by or source
        self.next_auto_at = None
        await self.publish()
        return True

    async def show_one_off(self, text, source="control panel", triggered_by=None):
        text = clean_text(text, 320)
        if not text:
            return False
        self.priority_queue.append({
            "text": text,
            "source": source,
            "triggeredBy": clean_text(triggered_by, 80) if triggered_by else None,
        })
        self.next_auto_at = None
        if self.active:
            # Let OBS play the current exit before replaying the complete
            # BREAKING NEWS entrance for the priority item.
            self.active = None
            self.transition_at = now_ms() + self.config["exitMs"] + 160
            await self.publish()
        elif not self.active and self.transition_at is None:
            await self.start_next_priority()
        else:
            await self.publish()
        return True

    async def start_next_priority(self):
        if not self.priority_queue:
            return False
        priority_items = []
        while self.priority_queue:
            item = self.priority_queue.popleft()
            priority_items.append({
                "messageId": None,
                "text": item["text"],
                "priority": True,
                "source": item["source"],
                "triggeredBy": item.get("triggeredBy"),
            })
        regular_items = self.next_regular_sequence()
        items = priority_items + regular_items
        first = priority_items[0]
        self.transition_at = None
        return await self.show(
            first["text"], None, first["source"], first.get("triggeredBy"),
            priority=True, items=items
        )

    async def hide(self, clear_sequence=True):
        self.active = None
        self.transition_at = None
        if clear_sequence:
            self.priority_queue.clear()
        self.next_auto_at = now_ms() + self.config["intervalSeconds"] * 1000 if self.config["autoEnabled"] else None
        await self.publish()

    async def finish_active(self):
        self.active = None
        self.transition_at = None
        self.next_auto_at = now_ms() + self.config["intervalSeconds"] * 1000 if self.config["autoEnabled"] else None
        await self.publish()

    async def scheduler_loop(self):
        while not self.shutdown.is_set():
            current = now_ms()
            if self.active and current >= self.active["hideAt"]:
                await self.finish_active()
            elif not self.active and self.transition_at and current >= self.transition_at:
                if self.priority_queue:
                    await self.start_next_priority()
                else:
                    self.transition_at = None
                    self.next_auto_at = current + self.config["intervalSeconds"] * 1000 if self.config["autoEnabled"] else None
                    await self.publish()
            elif not self.active and self.config["autoEnabled"] and self.next_auto_at and current >= self.next_auto_at:
                shown = await self.show_next("automatic")
                if not shown:
                    self.next_auto_at = current + self.config["intervalSeconds"] * 1000
                    await self.publish()
            try:
                await asyncio.wait_for(self.shutdown.wait(), timeout=0.2)
            except asyncio.TimeoutError:
                pass

    async def handle_streamer_event(self, packet):
        event = packet.get("event") if isinstance(packet, dict) else None
        if not isinstance(event, dict) or event.get("source") != "Twitch" or event.get("type") != "ChatMessage":
            return
        data = packet.get("data") if isinstance(packet.get("data"), dict) else {}
        argument = parse_command(data, self.config["command"])
        if argument is None:
            return
        user = data.get("user") if isinstance(data.get("user"), dict) else {}
        name = clean_text(user.get("name", data.get("userName", data.get("user", "Moderator"))), 80, "Moderator")
        if not self.config["commandEnabled"] or not is_moderator(data):
            self.status["deniedCommands"] += 1
            logging.info("Ignored unauthorized ticker command")
            await self.publish()
            return
        if not argument:
            await self.show_next("moderator command", name)
            return
        action, _, action_value = argument.partition(" ")
        action = action.lower()
        action_value = action_value.strip()
        if action == "add":
            text = clean_text(action_value, 320)
            if not text:
                await self.send_chat_messages([f"Usage: {self.config['command']} add <headline>"])
                return
            if len(self.config["messages"]) >= 100:
                await self.send_chat_messages(["NewsTicker already has the maximum of 100 saved items."])
                return
            self.config["messages"].append({"id": uuid.uuid4().hex, "text": text, "enabled": True})
            await self.persist_config()
            await self.send_chat_messages([
                f"NewsTicker: added item {len(self.config['messages'])}: {text}"
            ])
            return
        if action in ("delete", "remove", "del"):
            if not action_value.isdigit():
                await self.send_chat_messages([f"Usage: {self.config['command']} delete <item number>"])
                return
            position = int(action_value)
            if not 1 <= position <= len(self.config["messages"]):
                await self.send_chat_messages([
                    f"NewsTicker: item {position} does not exist. Use {self.config['command']} list."
                ])
                return
            deleted = self.config["messages"].pop(position - 1)
            await self.persist_config()
            await self.send_chat_messages([
                f"NewsTicker: deleted item {position}: {deleted['text']}"
            ])
            return
        if action == "list":
            await self.send_chat_messages(self.saved_item_messages())
            return
        if action == "help":
            command = self.config["command"]
            await self.send_chat_messages([
                f"NewsTicker commands: {command} (next), {command} <number> (show saved), "
                f"{command} <text> (one-off), {command} add <text>, {command} delete <number>, "
                f"{command} list, {command} help. Moderator/broadcaster only."
            ])
            return
        if argument.isdigit():
            selected = self.message_by_position(int(argument))
            if selected:
                await self.show(selected["text"], selected["id"], "moderator command", name)
            else:
                await self.send_chat_messages([
                    f"NewsTicker: saved item {argument} does not exist. Use {self.config['command']} list."
                ])
            return
        if self.config["allowCustomCommandText"]:
            await self.show_one_off(argument, "moderator command", name)
        else:
            await self.show_next("moderator command", name)

    def saved_item_messages(self):
        if not self.config["messages"]:
            return ["NewsTicker: no saved items. Add one with " + self.config["command"] + " add <headline>."]
        chunks = []
        current = "NewsTicker items: "
        for index, item in enumerate(self.config["messages"], 1):
            state = "" if item.get("enabled") else " [off]"
            entry = f"{index}. {item['text']}{state}"
            separator = " | " if current != "NewsTicker items: " else ""
            if len(current) + len(separator) + len(entry) > 430:
                chunks.append(current)
                current = "NewsTicker items (cont.): " + entry
            else:
                current += separator + entry
        chunks.append(current)
        return chunks

    async def send_chat_messages(self, messages):
        if not messages:
            return False
        if not self.streamer_socket or self.streamer_socket.closed or not self.streamer_chat_ready:
            self.status["chatReplies"] = "unavailable"
            self.status["chatReplyDetail"] = "Set the Streamer.bot WebSocket password to enable chat replies"
            await self.publish()
            logging.info("Streamer.bot chat reply skipped because the connection is not authenticated")
            return False
        try:
            for response_text in messages:
                await self.streamer_socket.send_json({
                    "request": "SendMessage",
                    "id": "ticker-chat-" + uuid.uuid4().hex,
                    "platform": "twitch",
                    "bot": True,
                    "internal": False,
                    "message": clean_text(response_text, 480),
                })
                if len(messages) > 1:
                    await asyncio.sleep(0.35)
            self.status["chatReplies"] = "ready"
            self.status["chatReplyDetail"] = "Command responses are enabled"
            return True
        except Exception:
            logging.exception("Could not send Streamer.bot chat response")
            self.status["chatReplies"] = "error"
            self.status["chatReplyDetail"] = "Streamer.bot rejected a chat response"
            await self.publish()
            return False

    async def streamer_loop(self):
        backoff = 1
        timeout = ClientTimeout(total=None, sock_connect=5)
        async with ClientSession(timeout=timeout) as session:
            while not self.shutdown.is_set():
                self.restart_streamer.clear()
                if not self.config["commandEnabled"]:
                    self.status.update(
                        streamer="disabled",
                        streamerDetail="Chat command is disabled",
                        chatReplies="unavailable",
                        chatReplyDetail="Chat command is disabled",
                    )
                    await self.publish()
                    try:
                        await asyncio.wait_for(self.restart_streamer.wait(), timeout=30)
                    except asyncio.TimeoutError:
                        continue
                    continue
                try:
                    self.status.update(streamer="connecting", streamerDetail="Connecting to Streamer.bot")
                    await self.publish()
                    async with session.ws_connect(self.config["streamerUrl"], heartbeat=15, max_msg_size=2_000_000) as ws:
                        self.streamer_socket = ws
                        self.streamer_chat_ready = False
                        first = None
                        try:
                            first = await asyncio.wait_for(ws.receive(), timeout=1.5)
                        except asyncio.TimeoutError:
                            pass
                        if first and first.type == WSMsgType.TEXT:
                            packet = json.loads(first.data)
                            if packet.get("request") == "Hello" and packet.get("authentication"):
                                password = self.config.get("streamerPassword", "")
                                if password:
                                    auth = packet["authentication"]
                                    secret = base64.b64encode(hashlib.sha256((password + auth["salt"]).encode()).digest()).decode()
                                    response = base64.b64encode(hashlib.sha256((secret + auth["challenge"]).encode()).digest()).decode()
                                    await ws.send_json({"request": "Authenticate", "id": "ticker-auth", "authentication": response})
                                    reply = await asyncio.wait_for(ws.receive_json(), timeout=5)
                                    if reply.get("status") != "ok":
                                        raise ValueError("Streamer.bot authentication failed")
                                    self.streamer_chat_ready = True
                            elif packet.get("request") == "Hello":
                                # No challenge means WebSocket authentication is disabled.
                                self.streamer_chat_ready = True
                            elif packet.get("event"):
                                await self.handle_streamer_event(packet)
                        await ws.send_json({
                            "request": "Subscribe",
                            "id": "ticker-subscribe",
                            "events": {"Twitch": ["ChatMessage"]},
                        })
                        backoff = 1
                        while not self.restart_streamer.is_set() and not self.shutdown.is_set():
                            try:
                                message = await asyncio.wait_for(ws.receive(), timeout=1)
                            except asyncio.TimeoutError:
                                continue
                            if message.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR):
                                break
                            if message.type != WSMsgType.TEXT:
                                continue
                            packet = json.loads(message.data)
                            if packet.get("id") == "ticker-subscribe":
                                if packet.get("status") != "ok":
                                    hint = " Check the password if Streamer.bot enforces authentication."
                                    raise ValueError("Streamer.bot rejected the event subscription." + hint)
                                self.status.update(streamer="connected", streamerDetail=f"Listening for {self.config['command']} from moderators")
                                self.status.update(
                                    chatReplies="ready" if self.streamer_chat_ready else "unavailable",
                                    chatReplyDetail="Command responses are enabled" if self.streamer_chat_ready else "Add the WebSocket password to enable chat replies",
                                )
                                await self.publish()
                            elif packet.get("event"):
                                self.status.update(streamer="connected", streamerDetail=f"Listening for {self.config['command']} from moderators")
                                await self.handle_streamer_event(packet)
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    detail = str(error) if isinstance(error, ValueError) else "Streamer.bot unavailable; reconnecting"
                    logging.warning("Streamer.bot connection unavailable: %s", type(error).__name__)
                    self.status.update(
                        streamer="disconnected",
                        streamerDetail=detail,
                        chatReplies="unavailable",
                        chatReplyDetail="Waiting for Streamer.bot",
                    )
                    await self.publish()
                finally:
                    self.streamer_socket = None
                    self.streamer_chat_ready = False
                if self.restart_streamer.is_set():
                    backoff = 1
                    continue
                try:
                    await asyncio.wait_for(self.restart_streamer.wait(), timeout=backoff)
                except asyncio.TimeoutError:
                    pass
                backoff = min(backoff * 2, 15)

    def backup_settings(self):
        if not self.settings_path.exists():
            return
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = DATA_ROOT / "backups" / f"settings-{stamp}.json"
        try:
            backup.write_bytes(self.settings_path.read_bytes())
            backups = sorted((DATA_ROOT / "backups").glob("settings-*.json"), key=lambda item: item.stat().st_mtime)
            for old in backups[:-10]:
                old.unlink()
        except OSError:
            logging.exception("Could not create settings backup")

    async def save_settings(self, raw):
        candidate = dict(raw)
        if candidate.pop("clearStreamerPassword", False):
            candidate["streamerPassword"] = ""
        elif not candidate.get("streamerPassword"):
            candidate.pop("streamerPassword", None)
        old_connection = (self.config.get("streamerUrl"), self.config.get("streamerPassword"), self.config.get("commandEnabled"))
        updated = normalize_settings(candidate, self.config)
        self.backup_settings()
        atomic_json(self.settings_path, updated)
        self.config = updated
        if not self.active:
            self.next_auto_at = now_ms() + updated["intervalSeconds"] * 1000 if updated["autoEnabled"] else None
        new_connection = (updated.get("streamerUrl"), updated.get("streamerPassword"), updated.get("commandEnabled"))
        if new_connection != old_connection:
            self.restart_streamer.set()
        await self.publish()

    def check_token(self, request):
        return secrets.compare_digest(request.headers.get("X-NewsTicker-Token", ""), self.csrf)

    async def control(self, _request):
        return web.FileResponse(WEB_ROOT / "index.html")

    async def overlay(self, _request):
        return web.FileResponse(WEB_ROOT / "overlay.html")

    async def api_state(self, _request):
        return web.json_response(self.snapshot(include_token=True), headers={"Cache-Control": "no-store"})

    async def api_save(self, request):
        if not self.check_token(request):
            raise web.HTTPForbidden(text="Invalid local control token")
        try:
            raw = await request.json()
        except (json.JSONDecodeError, ValueError):
            raise web.HTTPBadRequest(text="Invalid JSON")
        if not isinstance(raw, dict):
            raise web.HTTPBadRequest(text="Settings must be an object")
        await self.save_settings(raw)
        return web.json_response(self.snapshot(include_token=True))

    async def api_show(self, request):
        if not self.check_token(request):
            raise web.HTTPForbidden(text="Invalid local control token")
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            data = {}
        if data.get("text"):
            shown = await self.show_one_off(data["text"], "control panel")
        elif data.get("messageId"):
            selected = next((item for item in self.config["messages"] if item["id"] == data["messageId"]), None)
            shown = bool(selected) and await self.show(selected["text"], selected["id"], "control panel")
        else:
            shown = await self.show_next("control panel")
        if not shown:
            raise web.HTTPConflict(text="No enabled ticker messages")
        return web.json_response(self.snapshot(include_token=True))

    async def api_hide(self, request):
        if not self.check_token(request):
            raise web.HTTPForbidden(text="Invalid local control token")
        await self.hide()
        return web.json_response(self.snapshot(include_token=True))

    async def api_quit(self, request):
        if not self.check_token(request):
            raise web.HTTPForbidden(text="Invalid local control token")
        asyncio.get_running_loop().call_later(0.2, self.shutdown.set)
        return web.json_response({"ok": True})

    async def api_ping(self, _request):
        return web.json_response({"app": "NewsTicker", "version": VERSION})

    async def websocket(self, request):
        ws = web.WebSocketResponse(heartbeat=20, max_msg_size=128_000)
        await ws.prepare(request)
        self.clients.add(ws)
        await ws.send_json(self.snapshot())
        try:
            async for message in ws:
                if message.type == WSMsgType.TEXT and message.data == "ping":
                    await ws.send_str("pong")
        finally:
            self.clients.discard(ws)
        return ws

    def make_app(self):
        app = web.Application(client_max_size=256_000)
        app.router.add_get("/", self.control)
        app.router.add_get("/overlay", self.overlay)
        app.router.add_get("/ws", self.websocket)
        app.router.add_get("/api/state", self.api_state)
        app.router.add_get("/api/ping", self.api_ping)
        app.router.add_post("/api/settings", self.api_save)
        app.router.add_post("/api/show", self.api_show)
        app.router.add_post("/api/hide", self.api_hide)
        app.router.add_post("/api/quit", self.api_quit)
        app.router.add_static("/static/", WEB_ROOT, show_index=False, follow_symlinks=False)
        return app

    async def run(self):
        runner = web.AppRunner(self.make_app(), access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", self.port)
        try:
            await site.start()
        except OSError:
            if existing_app(self.port):
                webbrowser.open(f"http://127.0.0.1:{self.port}/")
                await runner.cleanup()
                return
            raise
        logging.info("NewsTicker %s started on 127.0.0.1:%s", VERSION, self.port)
        self.tasks = [
            asyncio.create_task(self.scheduler_loop(), name="scheduler"),
            asyncio.create_task(self.streamer_loop(), name="streamerbot"),
        ]
        if not self.no_browser:
            asyncio.get_running_loop().call_later(0.6, webbrowser.open, f"http://127.0.0.1:{self.port}/")
        await self.shutdown.wait()
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        for client in list(self.clients):
            with contextlib.suppress(Exception):
                await client.close(code=1001, message=b"App closing")
        await runner.cleanup()
        logging.info("NewsTicker stopped")


def existing_app(port):
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=0.8) as response:
            data = json.loads(response.read(2048))
            return data.get("app") == "NewsTicker"
    except Exception:
        return False


def configure_logging(diagnostics=False):
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    handlers = [RotatingFileHandler(DATA_ROOT / "app.log", maxBytes=800_000, backupCount=2, encoding="utf-8")]
    if diagnostics:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)


def show_error(message):
    if sys.platform == "win32":
        with contextlib.suppress(Exception):
            ctypes.windll.user32.MessageBoxW(None, message, "NewsTicker", 0x10)
            return
    print(message, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="NewsTicker local OBS overlay")
    parser.add_argument("--port", type=int)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--diagnostics", action="store_true")
    args = parser.parse_args()
    configure_logging(args.diagnostics)
    try:
        asyncio.run(NewsTicker(args.port, args.no_browser).run())
    except KeyboardInterrupt:
        pass
    except Exception as error:
        logging.exception("NewsTicker failed")
        show_error(f"NewsTicker could not start.\n\n{error}\n\nSee data\\app.log for details.")
        raise


if __name__ == "__main__":
    main()
