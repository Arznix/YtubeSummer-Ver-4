import os
import sys
from pathlib import Path
from typing import Optional
import re
from datetime import datetime, timedelta

from dotenv import load_dotenv
import keyring


KEYRING_SERVICE = "youtube-summarizer"
APP_NAME = "ytube-summarizer"


def get_config_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("ProgramData", "C:\\ProgramData")) / APP_NAME
    elif sys.platform == "darwin":
        return Path("/Library/Application Support") / APP_NAME
    else:
        return Path("/etc") / APP_NAME


class ConfigError(Exception):
    pass


class Config:
    MAX_CHANNELS = 100

    def __init__(self, env_file: Optional[str] = None):
        self.project_root = Path(__file__).parent.parent
        self.config_dir = get_config_dir()

        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            self.config_dir = self.project_root

        if env_file is None:
            env_file = self.config_dir / ".env"

        load_dotenv(env_file, override=True)
        self._validate_config()

    def _validate_config(self) -> None:
        required_vars = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "OLLAMA_HOST"]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            raise ConfigError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                f"Please run setup.py or create a .env file at: {self.config_dir / '.env'}"
            )

        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not re.match(r'^\d+:[A-Za-z0-9_-]+$', telegram_token):
            raise ConfigError("Invalid Telegram bot token format")

        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        if not ollama_host.startswith(("http://", "https://")):
            raise ConfigError("OLLAMA_HOST must start with http:// or https://")

        channel_ids = self.youtube_channel_ids
        if len(channel_ids) > self.MAX_CHANNELS:
            raise ConfigError(f"Too many channels: {len(channel_ids)}. Maximum is {self.MAX_CHANNELS}")

        frequency = self.schedule_frequency_hours
        if frequency < 1 or frequency > 24:
            raise ConfigError("SCHEDULE_FREQUENCY_HOURS must be between 1 and 24")

        start_time = self.schedule_start_time
        if start_time and not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', start_time):
            raise ConfigError("SCHEDULE_START_TIME must be in HH:MM format (24-hour)")

    @property
    def telegram_bot_token(self) -> str:
        token = keyring.get_password(KEYRING_SERVICE, "telegram_bot_token")
        if token:
            return token
        return os.getenv("TELEGRAM_BOT_TOKEN", "")

    @property
    def telegram_chat_id(self) -> str:
        chat_id = keyring.get_password(KEYRING_SERVICE, "telegram_chat_id")
        if chat_id:
            return chat_id
        return os.getenv("TELEGRAM_CHAT_ID", "")

    @property
    def telegram_bot_username(self) -> str:
        return os.getenv("TELEGRAM_BOT_USERNAME", "")

    @property
    def ollama_host(self) -> str:
        return os.getenv("OLLAMA_HOST", "http://localhost:11434")

    @property
    def ollama_model(self) -> str:
        return os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

    @property
    def database_path(self) -> Path:
        db_dir = self.config_dir / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "subscriptions_state.db"

    @property
    def youtube_channel_ids(self) -> list:
        channel_ids_str = os.getenv("YOUTUBE_CHANNEL_IDS", "")
        if not channel_ids_str:
            return []
        channels = [cid.strip() for cid in channel_ids_str.split(",") if cid.strip()]
        return channels[:self.MAX_CHANNELS]

    @property
    def schedule_start_time(self) -> Optional[str]:
        return os.getenv("SCHEDULE_START_TIME", None)

    @property
    def schedule_frequency_hours(self) -> int:
        try:
            return int(os.getenv("SCHEDULE_FREQUENCY_HOURS", "6"))
        except ValueError:
            return 6

    def get_next_run_time(self) -> datetime:
        now = datetime.now()

        if self.schedule_start_time:
            hours, minutes = map(int, self.schedule_start_time.split(":"))
            start_time_today = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            if start_time_today <= now:
                start_time_today += timedelta(days=1)
            return start_time_today
        else:
            return now + timedelta(minutes=5)

    def get_all_config(self) -> dict:
        return {
            "telegram_bot_token": "***" if self.telegram_bot_token else "",
            "telegram_chat_id": self.telegram_chat_id,
            "telegram_bot_username": self.telegram_bot_username,
            "ollama_host": self.ollama_host,
            "ollama_model": self.ollama_model,
            "config_dir": str(self.config_dir),
            "env_file": str(self.config_dir / ".env"),
            "database_path": str(self.database_path),
            "youtube_channel_ids": self.youtube_channel_ids,
            "channel_count": len(self.youtube_channel_ids),
            "max_channels": self.MAX_CHANNELS,
            "schedule_start_time": self.schedule_start_time or "Not set (defaults to now + 5 min)",
            "schedule_frequency_hours": self.schedule_frequency_hours,
            "next_run_time": self.get_next_run_time().strftime("%Y-%m-%d %H:%M:%S"),
            "project_root": str(self.project_root),
        }

    def print_config(self) -> None:
        config = self.get_all_config()
        print("Configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")

    @staticmethod
    def store_credentials(token: str, chat_id: str) -> None:
        keyring.set_password(KEYRING_SERVICE, "telegram_bot_token", token)
        keyring.set_password(KEYRING_SERVICE, "telegram_chat_id", chat_id)

    @staticmethod
    def clear_credentials() -> None:
        try:
            keyring.delete_password(KEYRING_SERVICE, "telegram_bot_token")
        except keyring.errors.PasswordDeleteError:
            pass
        try:
            keyring.delete_password(KEYRING_SERVICE, "telegram_chat_id")
        except keyring.errors.PasswordDeleteError:
            pass


def load_config(env_file: Optional[str] = None) -> Config:
    """
    Load and validate configuration.

    Args:
        env_file: Path to .env file. If None, uses the OS-appropriate default:

            Linux:   /etc/ytube-summarizer/.env
            macOS:   /Library/Application Support/ytube-summarizer/.env
            Windows: C:\\ProgramData\\ytube-summarizer\\.env

    Returns:
        Config object with validated configuration.

    Raises:
        ConfigError: If configuration is invalid or missing required variables.
    """
    return Config(env_file)


if __name__ == "__main__":
    try:
        config = load_config()
        config.print_config()
        print("\nConfiguration loaded successfully!")
    except ConfigError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
