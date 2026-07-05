#!/usr/bin/env python3
"""
Unit tests for web setup module.

Tests _load_env, _save_env, and config telegram_bot_username property.
"""

import unittest
import tempfile
import os
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv, get_key
import keyring


class TestWebSetupLoadEnv(unittest.TestCase):
    """Tests for WebSetupServer._load_env method."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.env_file = Path(self.test_dir) / ".env"
        # Clear all env vars to ensure tests are isolated
        for var in [
            "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_BOT_USERNAME",
            "OLLAMA_HOST", "OLLAMA_MODEL", "YOUTUBE_CHANNEL_IDS",
            "SCHEDULE_FREQUENCY_HOURS", "SCHEDULE_START_TIME",
        ]:
            os.environ.pop(var, None)
        # Clear keychain between tests
        from config import KEYRING_SERVICE
        for cred in ("telegram_bot_token", "telegram_chat_id"):
            try:
                keyring.delete_password(KEYRING_SERVICE, cred)
            except keyring.errors.PasswordDeleteError:
                pass

    def tearDown(self):
        # Clear any env vars we set
        for var in [
            "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_BOT_USERNAME",
            "OLLAMA_HOST", "OLLAMA_MODEL", "YOUTUBE_CHANNEL_IDS",
            "SCHEDULE_FREQUENCY_HOURS", "SCHEDULE_START_TIME",
        ]:
            os.environ.pop(var, None)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _make_server(self):
        from web_setup import WebSetupServer
        server = WebSetupServer.__new__(WebSetupServer)
        server.project_root = Path(self.test_dir)
        server.env_file = self.env_file
        return server

    def test_load_env_no_file(self):
        """_load_env returns defaults when .env does not exist."""
        server = self._make_server()
        result = server._load_env()

        self.assertEqual(result["TELEGRAM_BOT_TOKEN"], "")
        self.assertEqual(result["TELEGRAM_CHAT_ID"], "")
        self.assertEqual(result["TELEGRAM_BOT_USERNAME"], "")
        self.assertEqual(result["OLLAMA_HOST"], "http://localhost:11434")
        self.assertEqual(result["OLLAMA_MODEL"], "qwen2.5:1.5b")
        self.assertEqual(result["YOUTUBE_CHANNEL_IDS"], "")
        self.assertEqual(result["SCHEDULE_FREQUENCY_HOURS"], "6")
        self.assertEqual(result["SCHEDULE_START_TIME"], "")

    def test_load_env_reads_values(self):
        """_load_env reads values from .env file."""
        self.env_file.write_text(
            "TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz\n"
            "TELEGRAM_CHAT_ID=987654321\n"
            "TELEGRAM_BOT_USERNAME=test_bot\n"
            "OLLAMA_HOST=http://custom-host:11434\n"
            "OLLAMA_MODEL=qwen2.5-coder:1.5b\n"
            "YOUTUBE_CHANNEL_IDS=UCaaaa,UCbbbb\n"
            "SCHEDULE_FREQUENCY_HOURS=12\n"
            "SCHEDULE_START_TIME=08:30\n"
        )
        server = self._make_server()
        result = server._load_env()

        self.assertEqual(result["TELEGRAM_BOT_TOKEN"], "123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
        self.assertEqual(result["TELEGRAM_CHAT_ID"], "987654321")
        self.assertEqual(result["TELEGRAM_BOT_USERNAME"], "test_bot")
        self.assertEqual(result["OLLAMA_HOST"], "http://custom-host:11434")
        self.assertEqual(result["OLLAMA_MODEL"], "qwen2.5-coder:1.5b")
        self.assertEqual(result["YOUTUBE_CHANNEL_IDS"], "UCaaaa,UCbbbb")
        self.assertEqual(result["SCHEDULE_FREQUENCY_HOURS"], "12")
        self.assertEqual(result["SCHEDULE_START_TIME"], "08:30")

    def test_load_env_partial_file(self):
        """_load_env returns defaults for missing keys."""
        self.env_file.write_text(
            "TELEGRAM_BOT_TOKEN=123456789:ABCdef\n"
            "TELEGRAM_CHAT_ID=111\n"
        )
        server = self._make_server()
        result = server._load_env()

        self.assertEqual(result["TELEGRAM_BOT_TOKEN"], "123456789:ABCdef")
        self.assertEqual(result["TELEGRAM_CHAT_ID"], "111")
        self.assertEqual(result["TELEGRAM_BOT_USERNAME"], "")
        self.assertEqual(result["OLLAMA_HOST"], "http://localhost:11434")
        self.assertEqual(result["YOUTUBE_CHANNEL_IDS"], "")


class TestWebSetupSaveEnv(unittest.TestCase):
    """Tests for WebSetupServer._save_env method."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.env_file = Path(self.test_dir) / ".env"
        from config import KEYRING_SERVICE
        for cred in ("telegram_bot_token", "telegram_chat_id"):
            try:
                keyring.delete_password(KEYRING_SERVICE, cred)
            except keyring.errors.PasswordDeleteError:
                pass

    def tearDown(self):
        for var in [
            "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_BOT_USERNAME",
            "OLLAMA_HOST", "YOUTUBE_CHANNEL_IDS", "SCHEDULE_FREQUENCY_HOURS",
        ]:
            os.environ.pop(var, None)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _make_server(self):
        from web_setup import WebSetupServer
        server = WebSetupServer.__new__(WebSetupServer)
        server.project_root = Path(self.test_dir)
        server.env_file = self.env_file
        return server

    def test_save_env_creates_file(self):
        """_save_env creates .env if it doesn't exist."""
        self.assertFalse(self.env_file.exists())
        server = self._make_server()
        server._save_env({"TELEGRAM_BOT_TOKEN": "test_token"})
        self.assertTrue(self.env_file.exists())

    def test_save_env_writes_key(self):
        """_save_env stores sensitive keys in OS keychain."""
        from config import KEYRING_SERVICE
        server = self._make_server()
        server._save_env({"TELEGRAM_BOT_TOKEN": "123456789:ABCdef"})

        value = keyring.get_password(KEYRING_SERVICE, "telegram_bot_token")
        self.assertEqual(value, "123456789:ABCdef")

    def test_save_env_writes_multiple_keys(self):
        """_save_env stores sensitive keys in keychain, others in .env."""
        from config import KEYRING_SERVICE
        server = self._make_server()
        server._save_env({
            "TELEGRAM_BOT_TOKEN": "token123",
            "TELEGRAM_CHAT_ID": "999",
            "TELEGRAM_BOT_USERNAME": "my_bot",
        })

        self.assertEqual(keyring.get_password(KEYRING_SERVICE, "telegram_bot_token"), "token123")
        self.assertEqual(keyring.get_password(KEYRING_SERVICE, "telegram_chat_id"), "999")
        self.assertEqual(get_key(str(self.env_file), "TELEGRAM_BOT_USERNAME"), "my_bot")

    def test_save_env_updates_existing_key(self):
        """_save_env overwrites an existing key in keychain."""
        from config import KEYRING_SERVICE
        keyring.set_password(KEYRING_SERVICE, "telegram_bot_token", "old_token")
        server = self._make_server()
        server._save_env({"TELEGRAM_BOT_TOKEN": "new_token"})

        value = keyring.get_password(KEYRING_SERVICE, "telegram_bot_token")
        self.assertEqual(value, "new_token")

    def test_save_env_preserves_other_keys(self):
        """_save_env does not remove unrelated keys from .env."""
        from config import KEYRING_SERVICE
        self.env_file.write_text(
            "OLLAMA_HOST=http://localhost:11434\n"
        )
        keyring.set_password(KEYRING_SERVICE, "telegram_bot_token", "keep_me")
        server = self._make_server()
        server._save_env({"TELEGRAM_CHAT_ID": "123"})

        self.assertEqual(keyring.get_password(KEYRING_SERVICE, "telegram_bot_token"), "keep_me")
        self.assertEqual(get_key(str(self.env_file), "OLLAMA_HOST"), "http://localhost:11434")
        self.assertEqual(keyring.get_password(KEYRING_SERVICE, "telegram_chat_id"), "123")

    def test_save_env_channels_list(self):
        """_save_env handles comma-separated channel IDs."""
        server = self._make_server()
        server._save_env({"YOUTUBE_CHANNEL_IDS": "UCaaa,UCbbb,UCccc"})

        value = get_key(str(self.env_file), "YOUTUBE_CHANNEL_IDS")
        self.assertEqual(value, "UCaaa,UCbbb,UCccc")

    def test_save_env_frequency(self):
        """_save_env writes frequency as string."""
        server = self._make_server()
        server._save_env({"SCHEDULE_FREQUENCY_HOURS": "12"})

        value = get_key(str(self.env_file), "SCHEDULE_FREQUENCY_HOURS")
        self.assertEqual(value, "12")


class TestConfigUsername(unittest.TestCase):
    """Tests for Config.telegram_bot_username property."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.env_file = Path(self.test_dir) / ".env"
        self.original_env = {}
        for var in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "OLLAMA_HOST", "TELEGRAM_BOT_USERNAME"]:
            self.original_env[var] = os.environ.get(var)

    def tearDown(self):
        for var, value in self.original_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _set_env(self, content):
        self.env_file.write_text(content)
        load_dotenv(self.env_file, override=True)

    def test_username_property_returns_value(self):
        """telegram_bot_username returns the env var value."""
        self._set_env(
            "TELEGRAM_BOT_TOKEN=123456789:ABCdef\n"
            "TELEGRAM_CHAT_ID=111\n"
            "OLLAMA_HOST=http://localhost:11434\n"
            "TELEGRAM_BOT_USERNAME=my_test_bot\n"
        )
        from config import Config
        config = Config()
        self.assertEqual(config.telegram_bot_username, "my_test_bot")

    def test_username_property_default_empty(self):
        """telegram_bot_username returns empty string when unset."""
        self._set_env(
            "TELEGRAM_BOT_TOKEN=123456789:ABCdef\n"
            "TELEGRAM_CHAT_ID=111\n"
            "OLLAMA_HOST=http://localhost:11434\n"
        )
        os.environ.pop("TELEGRAM_BOT_USERNAME", None)
        from config import Config
        config = Config()
        self.assertEqual(config.telegram_bot_username, "")

    def test_get_all_config_includes_username(self):
        """get_all_config dict contains telegram_bot_username."""
        self._set_env(
            "TELEGRAM_BOT_TOKEN=123456789:ABCdef\n"
            "TELEGRAM_CHAT_ID=111\n"
            "OLLAMA_HOST=http://localhost:11434\n"
            "TELEGRAM_BOT_USERNAME=hello_bot\n"
        )
        from config import Config
        config = Config()
        all_config = config.get_all_config()
        self.assertIn("telegram_bot_username", all_config)
        self.assertEqual(all_config["telegram_bot_username"], "hello_bot")

    def test_username_not_required(self):
        """Config loads successfully without TELEGRAM_BOT_USERNAME."""
        self._set_env(
            "TELEGRAM_BOT_TOKEN=123456789:ABCdef\n"
            "TELEGRAM_CHAT_ID=111\n"
            "OLLAMA_HOST=http://localhost:11434\n"
        )
        os.environ.pop("TELEGRAM_BOT_USERNAME", None)
        from config import Config
        config = Config()
        self.assertIsNotNone(config)


class TestMaskToken(unittest.TestCase):
    """Tests for the _mask_token helper function."""

    def test_mask_long_token(self):
        """Long token shows only last 4 characters."""
        from web_setup import _mask_token
        result = _mask_token("123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
        self.assertEqual(result, "***wxyz")

    def test_mask_short_token(self):
        """Token of 4 or fewer characters returns '***'."""
        from web_setup import _mask_token
        self.assertEqual(_mask_token("abc"), "***")
        self.assertEqual(_mask_token("ab"), "***")
        self.assertEqual(_mask_token("a"), "***")

    def test_mask_empty_token(self):
        """Empty token returns '***'."""
        from web_setup import _mask_token
        self.assertEqual(_mask_token(""), "***")

    def test_mask_exactly_four_chars(self):
        """Token of exactly 4 chars returns '***'."""
        from web_setup import _mask_token
        self.assertEqual(_mask_token("abcd"), "***")

    def test_mask_five_chars(self):
        """Token of 5 chars shows last 4."""
        from web_setup import _mask_token
        self.assertEqual(_mask_token("abcde"), "***bcde")


if __name__ == "__main__":
    unittest.main(verbosity=2)
