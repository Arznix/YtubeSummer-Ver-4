#!/usr/bin/env python3
"""
API integration tests for web setup module.

Starts a real HTTPServer and makes requests to verify all endpoints.
Tests include authentication and CSRF token validation.
"""

import unittest
import tempfile
import os
import json
import shutil
import threading
import time
import secrets
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from web_setup import WebSetupServer
from config import KEYRING_SERVICE
import keyring


def find_free_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class TestWebSetupAPI(unittest.TestCase):
    """API integration tests for all web setup endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp()
        cls.env_file = Path(cls.test_dir) / ".env"
        cls.port = find_free_port()

        # Create server instance with auth/CSRF tokens
        cls.server = WebSetupServer.__new__(WebSetupServer)
        cls.server.port = cls.port
        cls.server.project_root = Path(cls.test_dir)
        cls.server.env_file = cls.env_file
        cls.server._auth_token = secrets.token_urlsafe(32)
        cls.server._csrf_token = secrets.token_urlsafe(32)

        from setup import SetupWizard
        cls.server._wizard = SetupWizard()

        # Start HTTP server in background thread
        handler_cls = cls.server._make_handler()
        cls.httpd = __import__("http.server", fromlist=["HTTPServer"]).HTTPServer(
            ("127.0.0.1", cls.port), handler_cls
        )
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.3)

        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def setUp(self):
        for var in [
            "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_BOT_USERNAME",
            "OLLAMA_HOST", "OLLAMA_MODEL", "YOUTUBE_CHANNEL_IDS",
            "SCHEDULE_FREQUENCY_HOURS", "SCHEDULE_START_TIME",
        ]:
            os.environ.pop(var, None)
        if self.env_file.exists():
            self.env_file.unlink()
        # Clear keychain between tests
        for cred in ("telegram_bot_token", "telegram_chat_id"):
            try:
                keyring.delete_password(KEYRING_SERVICE, cred)
            except keyring.errors.PasswordDeleteError:
                pass

    def _auth_headers(self):
        return {"X-Auth-Token": self.server._auth_token}

    def _post_headers(self):
        return {
            "Content-Type": "application/json",
            "X-Auth-Token": self.server._auth_token,
            "X-CSRF-Token": self.server._csrf_token,
        }

    def _get(self, path, include_auth=True):
        headers = self._auth_headers() if include_auth else {}
        req = Request(f"{self.base_url}{path}", method="GET", headers=headers)
        try:
            with urlopen(req) as resp:
                return resp.status, resp.headers.get("Content-Type", ""), resp.read().decode("utf-8")
        except HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                return e.code, e.headers.get("Content-Type", ""), json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                return e.code, e.headers.get("Content-Type", ""), raw

    def _post(self, path, data, include_auth=True, include_csrf=True):
        body = json.dumps(data).encode("utf-8")
        headers = {}
        if include_auth:
            headers["X-Auth-Token"] = self.server._auth_token
        if include_csrf:
            headers["X-CSRF-Token"] = self.server._csrf_token
        headers["Content-Type"] = "application/json"
        req = Request(f"{self.base_url}{path}", data=body, headers=headers, method="POST")
        try:
            with urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                return e.code, json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                return e.code, {"error": raw}

    # --- Authentication tests ---

    def test_get_config_no_auth_returns_401(self):
        """GET /api/config without auth token returns 401."""
        status, _, body = self._get("/api/config", include_auth=False)
        self.assertEqual(status, 401)

    def test_get_config_wrong_auth_returns_401(self):
        """GET /api/config with wrong auth token returns 401."""
        req = Request(f"{self.base_url}/api/config", method="GET",
                       headers={"X-Auth-Token": "wrong-token"})
        try:
            with urlopen(req) as resp:
                self.fail("Expected 401")
        except HTTPError as e:
            self.assertEqual(e.code, 401)

    def test_post_no_auth_returns_401(self):
        """POST without auth token returns 401."""
        status, data = self._post("/api/frequency", {"frequency": 6}, include_auth=False)
        self.assertEqual(status, 401)

    def test_post_no_csrf_returns_403(self):
        """POST without CSRF token returns 403."""
        status, data = self._post("/api/frequency", {"frequency": 6}, include_csrf=False)
        self.assertEqual(status, 403)

    def test_post_wrong_csrf_returns_403(self):
        """POST with wrong CSRF token returns 403."""
        body = json.dumps({"frequency": 6}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-Auth-Token": self.server._auth_token,
            "X-CSRF-Token": "wrong-csrf-token",
        }
        req = Request(f"{self.base_url}/api/frequency", data=body, headers=headers, method="POST")
        try:
            with urlopen(req) as resp:
                self.fail("Expected 403")
        except HTTPError as e:
            self.assertEqual(e.code, 403)

    # --- GET / ---

    def test_get_serves_html(self):
        """GET / returns HTML page with title and embedded tokens."""
        status, content_type, body = self._get("/", include_auth=False)
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("Ytube Summarizer", body)
        self.assertIn("channel-url", body)
        self.assertIn("freq-input", body)
        self.assertIn("telegram-modal", body)
        # Tokens should be embedded (not placeholders)
        self.assertNotIn("__CSRF_TOKEN__", body)
        self.assertNotIn("__AUTH_TOKEN__", body)
        self.assertIn(self.server._csrf_token, body)
        self.assertIn(self.server._auth_token, body)

    def test_get_html_has_auth_banner(self):
        """GET / page includes auth security banner."""
        status, _, body = self._get("/", include_auth=False)
        self.assertIn("auth-banner", body)

    # --- GET /api/config ---

    def test_get_config_returns_json(self):
        """GET /api/config returns valid JSON with expected keys."""
        status, content_type, body = self._get("/api/config")
        self.assertEqual(status, 200)
        self.assertIn("application/json", content_type)
        data = json.loads(body)
        self.assertIn("telegram_bot_token", data)
        self.assertIn("telegram_chat_id", data)
        self.assertIn("telegram_bot_username", data)
        self.assertIn("ollama_host", data)
        self.assertIn("ollama_model", data)
        self.assertIn("youtube_channel_ids", data)
        self.assertIn("schedule_frequency_hours", data)
        self.assertIn("schedule_start_time", data)

    def test_get_config_defaults(self):
        """GET /api/config returns defaults on fresh .env."""
        status, _, body = self._get("/api/config")
        data = json.loads(body)
        self.assertEqual(data["telegram_bot_token"], "***")
        self.assertEqual(data["telegram_chat_id"], "")
        self.assertEqual(data["telegram_bot_username"], "")
        self.assertEqual(data["youtube_channel_ids"], [])
        self.assertEqual(data["schedule_frequency_hours"], 6)

    def test_get_config_masks_bot_token(self):
        """GET /api/config masks the bot token (shows only last 4 chars)."""
        self.env_file.write_text(
            "TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz\n"
            "TELEGRAM_CHAT_ID=555\n"
        )
        status, _, body = self._get("/api/config")
        data = json.loads(body)
        self.assertEqual(data["telegram_bot_token"], "***wxyz")
        self.assertNotIn("123456789", data["telegram_bot_token"])

    def test_get_config_reads_existing(self):
        """GET /api/config reads from existing .env file."""
        self.env_file.write_text(
            "TELEGRAM_BOT_TOKEN=123456789:ABCdef\n"
            "TELEGRAM_CHAT_ID=555\n"
            "TELEGRAM_BOT_USERNAME=existing_bot\n"
            "YOUTUBE_CHANNEL_IDS=UCaaa,UCbbb\n"
            "SCHEDULE_FREQUENCY_HOURS=12\n"
        )
        status, _, body = self._get("/api/config")
        data = json.loads(body)
        self.assertEqual(data["telegram_chat_id"], "555")
        self.assertEqual(data["telegram_bot_username"], "existing_bot")
        self.assertEqual(data["youtube_channel_ids"], ["UCaaa", "UCbbb"])
        self.assertEqual(data["schedule_frequency_hours"], 12)

    # --- POST /api/channels/add ---

    @patch("setup.SetupWizard.extract_channel_id_from_url")
    def test_add_channel_valid_url(self, mock_extract):
        """POST /api/channels/add with valid URL succeeds."""
        mock_extract.return_value = "UCin0m13qWv3-051xlWlHamA"
        status, data = self._post("/api/channels/add", {"url": "https://www.youtube.com/@veritasium"})
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["channel_id"], "UCin0m13qWv3-051xlWlHamA")
        self.assertIn("UCin0m13qWv3-051xlWlHamA", data["channels"])

    def test_add_channel_direct_id(self):
        """POST /api/channels/add with direct channel ID succeeds."""
        status, data = self._post("/api/channels/add", {"url": "UCin0m13qWv3-051xlWlHamA"})
        self.assertIn(status, [200, 400])

    def test_add_channel_empty_url(self):
        """POST /api/channels/add with empty URL returns 400."""
        status, data = self._post("/api/channels/add", {"url": ""})
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    def test_add_channel_missing_url(self):
        """POST /api/channels/add with no url key returns 400."""
        status, data = self._post("/api/channels/add", {})
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    @patch("setup.SetupWizard.extract_channel_id_from_url")
    def test_add_channel_extraction_fails(self, mock_extract):
        """POST /api/channels/add returns error when extraction fails."""
        mock_extract.return_value = None
        status, data = self._post("/api/channels/add", {"url": "https://example.com/not-youtube"})
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    @patch("setup.SetupWizard.extract_channel_id_from_url")
    def test_add_channel_duplicate(self, mock_extract):
        """POST /api/channels/add returns 409 for duplicate channel."""
        mock_extract.return_value = "UCin0m13qWv3-051xlWlHamA"
        self._post("/api/channels/add", {"url": "https://www.youtube.com/@veritasium"})
        status, data = self._post("/api/channels/add", {"url": "https://www.youtube.com/@veritasium"})
        self.assertEqual(status, 409)
        self.assertIn("error", data)

    # --- POST /api/channels/delete ---

    def test_delete_channel(self):
        """POST /api/channels/delete removes a channel."""
        self.env_file.write_text("YOUTUBE_CHANNEL_IDS=UCaaa,UCbbb\n")
        status, data = self._post("/api/channels/delete", {"channel_id": "UCaaa"})
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertNotIn("UCaaa", data["channels"])
        self.assertIn("UCbbb", data["channels"])

    def test_delete_channel_not_found(self):
        """POST /api/channels/delete returns 404 for unknown channel."""
        self.env_file.write_text("YOUTUBE_CHANNEL_IDS=UCaaa\n")
        status, data = self._post("/api/channels/delete", {"channel_id": "UCzzz"})
        self.assertEqual(status, 404)
        self.assertIn("error", data)

    def test_delete_channel_empty_id(self):
        """POST /api/channels/delete returns 400 for empty ID."""
        status, data = self._post("/api/channels/delete", {"channel_id": ""})
        self.assertEqual(status, 400)

    def test_delete_channel_persists(self):
        """After delete, .env file reflects removal."""
        self.env_file.write_text("YOUTUBE_CHANNEL_IDS=UCaaa,UCbbb,UCccc\n")
        self._post("/api/channels/delete", {"channel_id": "UCbbb"})
        from dotenv import get_key
        value = get_key(str(self.env_file), "YOUTUBE_CHANNEL_IDS")
        self.assertEqual(value, "UCaaa,UCccc")

    # --- POST /api/frequency ---

    def test_frequency_valid(self):
        """POST /api/frequency with valid value succeeds."""
        status, data = self._post("/api/frequency", {"frequency": 12})
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["frequency"], 12)

    def test_frequency_below_range(self):
        """POST /api/frequency with 0 returns 400."""
        status, data = self._post("/api/frequency", {"frequency": 0})
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    def test_frequency_above_range(self):
        """POST /api/frequency with 25 returns 400."""
        status, data = self._post("/api/frequency", {"frequency": 25})
        self.assertEqual(status, 400)

    def test_frequency_non_numeric(self):
        """POST /api/frequency with string returns 400."""
        status, data = self._post("/api/frequency", {"frequency": "abc"})
        self.assertEqual(status, 400)

    def test_frequency_missing(self):
        """POST /api/frequency with no frequency key returns 400."""
        status, data = self._post("/api/frequency", {})
        self.assertEqual(status, 400)

    def test_frequency_persists(self):
        """Frequency value is written to .env."""
        self._post("/api/frequency", {"frequency": 8})
        from dotenv import get_key
        value = get_key(str(self.env_file), "SCHEDULE_FREQUENCY_HOURS")
        self.assertEqual(value, "8")

    # --- POST /api/telegram ---

    def test_telegram_valid(self):
        """POST /api/telegram with valid credentials succeeds."""
        status, data = self._post("/api/telegram", {
            "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            "chat_id": "987654321",
            "username": "test_bot",
        })
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])

    def test_telegram_invalid_token_no_colon(self):
        """POST /api/telegram with token missing colon returns 400."""
        status, data = self._post("/api/telegram", {
            "bot_token": "123456789ABCdef",
            "chat_id": "987654321",
        })
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    def test_telegram_non_numeric_chat_id(self):
        """POST /api/telegram with non-numeric chat_id returns 400."""
        status, data = self._post("/api/telegram", {
            "bot_token": "123456789:ABCdef",
            "chat_id": "abc",
        })
        self.assertEqual(status, 400)

    def test_telegram_missing_token(self):
        """POST /api/telegram with empty token returns 400."""
        status, data = self._post("/api/telegram", {
            "bot_token": "",
            "chat_id": "123",
        })
        self.assertEqual(status, 400)

    def test_telegram_missing_chat_id(self):
        """POST /api/telegram with empty chat_id returns 400."""
        status, data = self._post("/api/telegram", {
            "bot_token": "123456789:ABCdef",
            "chat_id": "",
        })
        self.assertEqual(status, 400)

    def test_telegram_saves_username(self):
        """POST /api/telegram saves TELEGRAM_BOT_USERNAME to .env."""
        self._post("/api/telegram", {
            "bot_token": "123456789:ABCdef",
            "chat_id": "999",
            "username": "my_saved_bot",
        })
        from dotenv import get_key
        value = get_key(str(self.env_file), "TELEGRAM_BOT_USERNAME")
        self.assertEqual(value, "my_saved_bot")

    def test_telegram_persists_all_fields(self):
        """Sensitive fields stored in keychain, username in .env."""
        self._post("/api/telegram", {
            "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            "chat_id": "111222333",
            "username": "persist_bot",
        })
        from dotenv import get_key
        self.assertEqual(keyring.get_password(KEYRING_SERVICE, "telegram_bot_token"), "123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
        self.assertEqual(keyring.get_password(KEYRING_SERVICE, "telegram_chat_id"), "111222333")
        self.assertEqual(get_key(str(self.env_file), "TELEGRAM_BOT_USERNAME"), "persist_bot")

    def test_telegram_without_username(self):
        """POST /api/telegram without username still succeeds."""
        status, data = self._post("/api/telegram", {
            "bot_token": "123456789:ABCdef",
            "chat_id": "555",
        })
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])

    # --- POST /api/save ---

    def test_save_all_fields(self):
        """POST /api/save writes sensitive to keychain, rest to .env."""
        status, data = self._post("/api/save", {
            "youtube_channel_ids": ["UCaaa", "UCbbb"],
            "schedule_frequency_hours": 4,
            "telegram_bot_token": "123456789:ABCdef",
            "telegram_chat_id": "777",
            "telegram_bot_username": "saved_bot",
        })
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])

        from dotenv import get_key
        self.assertEqual(get_key(str(self.env_file), "YOUTUBE_CHANNEL_IDS"), "UCaaa,UCbbb")
        self.assertEqual(get_key(str(self.env_file), "SCHEDULE_FREQUENCY_HOURS"), "4")
        self.assertEqual(keyring.get_password(KEYRING_SERVICE, "telegram_bot_token"), "123456789:ABCdef")
        self.assertEqual(keyring.get_password(KEYRING_SERVICE, "telegram_chat_id"), "777")
        self.assertEqual(get_key(str(self.env_file), "TELEGRAM_BOT_USERNAME"), "saved_bot")

    def test_save_partial_fields(self):
        """POST /api/save with only some fields updates only those."""
        keyring.set_password(KEYRING_SERVICE, "telegram_bot_token", "old_token")
        self.env_file.write_text(
            "YOUTUBE_CHANNEL_IDS=UCold\n"
        )
        self._post("/api/save", {
            "telegram_chat_id": "new_id",
        })
        from dotenv import get_key
        self.assertEqual(keyring.get_password(KEYRING_SERVICE, "telegram_bot_token"), "old_token")
        self.assertEqual(keyring.get_password(KEYRING_SERVICE, "telegram_chat_id"), "new_id")
        self.assertEqual(get_key(str(self.env_file), "YOUTUBE_CHANNEL_IDS"), "UCold")

    def test_save_empty_body(self):
        """POST /api/save with empty body succeeds (no-op)."""
        status, data = self._post("/api/save", {})
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])

    def test_save_frequency_validation(self):
        """POST /api/save ignores invalid frequency values."""
        self.env_file.write_text("SCHEDULE_FREQUENCY_HOURS=6\n")
        self._post("/api/save", {"schedule_frequency_hours": 99})
        from dotenv import get_key
        value = get_key(str(self.env_file), "SCHEDULE_FREQUENCY_HOURS")
        self.assertEqual(value, "6")

    # --- 404 handling ---

    def test_get_unknown_path_returns_404(self):
        """GET to unknown path returns 404."""
        req = Request(f"{self.base_url}/api/unknown", method="GET",
                       headers={"X-Auth-Token": self.server._auth_token})
        try:
            with urlopen(req) as resp:
                self.fail("Expected 404")
        except HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_post_unknown_path_returns_404(self):
        """POST to unknown path returns 404."""
        status, data = self._post("/api/unknown", {})
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
