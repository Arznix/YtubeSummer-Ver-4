import json
import os
import sys
from pathlib import Path
from typing import Optional
import re
from datetime import datetime, timedelta

from dotenv import load_dotenv

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False
    keyring = None

_KEYRING_AVAILABLE = None

def _get_flags_path() -> Path:
    return get_config_dir() / "flags.txt"

def _read_flag(flag_name: str) -> str:
    flags_path = _get_flags_path()
    if not flags_path.exists():
        return "0"
    try:
        for line in flags_path.read_text().splitlines():
            line = line.strip()
            if line.startswith(flag_name + "="):
                return line.split("=", 1)[1]
    except (OSError, UnicodeDecodeError):
        pass
    return "0"

def _write_flag(flag_name: str, value: str) -> None:
    flags_path = _get_flags_path()
    try:
        flags_path.parent.mkdir(parents=True, exist_ok=True)
        if flags_path.exists():
            lines = flags_path.read_text().splitlines()
        else:
            lines = []
        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(flag_name + "="):
                lines[i] = f"{flag_name}={value}"
                found = True
                break
        if not found:
            lines.append(f"{flag_name}={value}")
        flags_path.write_text("\n".join(lines) + "\n")
    except (OSError, UnicodeDecodeError):
        pass


KEYRING_SERVICE = "youtube-summarizer"
APP_NAME = "ytube-summarizer"


def _get_credential_file(config_dir: Path) -> Path:
    return config_dir / ".credentials.json"


def _read_credential_file(config_dir: Path) -> dict:
    cred_file = _get_credential_file(config_dir)
    if cred_file.exists():
        try:
            return json.loads(cred_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _write_credential_file(config_dir: Path, creds: dict) -> None:
    cred_file = _get_credential_file(config_dir)
    cred_file.write_text(json.dumps(creds, indent=2))
    # Restrict permissions on Unix-like systems
    if sys.platform != "win32":
        cred_file.chmod(0o600)


def _keyring_available() -> bool:
    global _KEYRING_AVAILABLE
    if _KEYRING_AVAILABLE is not None:
        return _KEYRING_AVAILABLE
    if not HAS_KEYRING:
        _KEYRING_AVAILABLE = False
        return False
    ring_flg = _read_flag("ring-flg")
    if ring_flg != "1":
        _KEYRING_AVAILABLE = False
        return False
    try:
        keyring.get_password("__probe__", "__probe__")
        _KEYRING_AVAILABLE = True
    except Exception:
        _KEYRING_AVAILABLE = False
    return _KEYRING_AVAILABLE


def _keyring_get(service: str, key: str) -> Optional[str]:
    """Get a credential from the system keyring. Returns None if keyring is
    unavailable or no credentials have been stored yet."""
    if not _keyring_available():
        return None
    try:
        return keyring.get_password(service, key)
    except Exception:
        return None


def _keyring_set(service: str, key: str, value: str) -> bool:
    """Store a credential in the system keyring. Sets ring-flg=1 on success.
    Returns True on success, False if keyring is unavailable."""
    if not HAS_KEYRING:
        return False
    try:
        keyring.set_password(service, key, value)
        _write_flag("ring-flg", "1")
        global _KEYRING_AVAILABLE
        _KEYRING_AVAILABLE = True
        return True
    except Exception:
        return False


def _keyring_delete(service: str, key: str) -> None:
    """Delete a credential from the system keyring."""
    if not _keyring_available():
        return
    try:
        keyring.delete_password(service, key)
    except keyring.errors.PasswordDeleteError:
        pass
    except Exception:
        pass


def get_config_dir() -> Path:
    return Path.home() / "Documents" / "TheConfigs"


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
        required_vars = {
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TELEGRAM_CHAT_ID": self.telegram_chat_id,
            "OLLAMA_HOST": os.getenv("OLLAMA_HOST"),
        }

        missing_vars = []
        for var, value in required_vars.items():
            if not value:
                missing_vars.append(var)

        if missing_vars:
            raise ConfigError(
                f"Missing required configuration: {', '.join(missing_vars)}\n"
                f"Please run setup.py to store credentials in the system keyring."
            )

        telegram_token = self.telegram_bot_token
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

        delay_min = self.youtube_request_delay_min
        delay_max = self.youtube_request_delay_max
        if delay_min < 1:
            raise ConfigError("YOUTUBE_REQUEST_DELAY_MIN must be at least 1 second")
        if delay_max < delay_min:
            raise ConfigError("YOUTUBE_REQUEST_DELAY_MAX must be >= YOUTUBE_REQUEST_DELAY_MIN")

        proxies = self.youtube_proxy_list
        for proxy in proxies:
            if not proxy.startswith(("http://", "https://", "socks4://", "socks5://")):
                raise ConfigError(f"Invalid proxy URL: {proxy}. Must start with http://, https://, socks4://, or socks5://")

    @property
    def telegram_bot_token(self) -> str:
        token = _keyring_get(KEYRING_SERVICE, "telegram_bot_token")
        if token:
            return token
        creds = _read_credential_file(self.config_dir)
        if "telegram_bot_token" in creds:
            return creds["telegram_bot_token"]
        return os.getenv("TELEGRAM_BOT_TOKEN", "")

    @property
    def telegram_chat_id(self) -> str:
        chat_id = _keyring_get(KEYRING_SERVICE, "telegram_chat_id")
        if chat_id:
            return chat_id
        creds = _read_credential_file(self.config_dir)
        if "telegram_chat_id" in creds:
            return creds["telegram_chat_id"]
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

    @property
    def youtube_request_delay_min(self) -> float:
        try:
            return float(os.getenv("YOUTUBE_REQUEST_DELAY_MIN", os.getenv("YOUTUBE_REQUEST_DELAY", "60")))
        except ValueError:
            return 60.0

    @property
    def youtube_request_delay_max(self) -> float:
        try:
            return float(os.getenv("YOUTUBE_REQUEST_DELAY_MAX", "240"))
        except ValueError:
            return 240.0

    @property
    def youtube_proxy_list(self) -> list:
        proxies_str = os.getenv("YOUTUBE_PROXY_LIST", "")
        if not proxies_str:
            return []
        return [p.strip() for p in proxies_str.split(",") if p.strip()]

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
            "youtube_request_delay_min": self.youtube_request_delay_min,
            "youtube_request_delay_max": self.youtube_request_delay_max,
            "youtube_proxy_list": self.youtube_proxy_list,
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
        config_dir = get_config_dir()
        ok = _keyring_set(KEYRING_SERVICE, "telegram_bot_token", token) and \
             _keyring_set(KEYRING_SERVICE, "telegram_chat_id", chat_id)
        if not ok:
            creds = _read_credential_file(config_dir)
            creds["telegram_bot_token"] = token
            creds["telegram_chat_id"] = chat_id
            _write_credential_file(config_dir, creds)

    @staticmethod
    def clear_credentials() -> None:
        config_dir = get_config_dir()
        _keyring_delete(KEYRING_SERVICE, "telegram_bot_token")
        _keyring_delete(KEYRING_SERVICE, "telegram_chat_id")
        cred_file = _get_credential_file(config_dir)
        if cred_file.exists():
            try:
                cred_file.unlink()
            except OSError:
                pass


def load_config(env_file: Optional[str] = None) -> Config:
    """
    Load and validate configuration.

    Args:
        env_file: Path to .env file. If None, defaults to:

            ~/Documents/TheConfigs/.env

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
