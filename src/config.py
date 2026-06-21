import os
from pathlib import Path
from typing import Optional
import re
from datetime import datetime, timedelta

from dotenv import load_dotenv


class ConfigError(Exception):
    """Configuration error exception."""
    pass


class Config:
    """Configuration manager for the YouTube summarizer pipeline."""
    
    MAX_CHANNELS = 100
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            env_file: Path to .env file. If None, uses default .env in project root.
        """
        self.project_root = Path(__file__).parent.parent
        
        if env_file is None:
            env_file = self.project_root / ".env"
        
        # Load environment variables (override system env vars with .env values)
        load_dotenv(env_file, override=True)
        
        # Validate and set configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate required configuration variables."""
        required_vars = [
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHAT_ID",
            "OLLAMA_HOST"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ConfigError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                f"Please copy .env.example to .env and fill in the values."
            )
        
        # Validate Telegram bot token format
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not re.match(r'^\d+:[A-Za-z0-9_-]+$', telegram_token):
            raise ConfigError("Invalid Telegram bot token format")
        
        # Validate Ollama host URL
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        if not ollama_host.startswith(("http://", "https://")):
            raise ConfigError("OLLAMA_HOST must start with http:// or https://")
        
        # Validate channel count
        channel_ids = self.youtube_channel_ids
        if len(channel_ids) > self.MAX_CHANNELS:
            raise ConfigError(f"Too many channels: {len(channel_ids)}. Maximum is {self.MAX_CHANNELS}")
        
        # Validate schedule frequency
        frequency = self.schedule_frequency_hours
        if frequency < 1 or frequency > 24:
            raise ConfigError("SCHEDULE_FREQUENCY_HOURS must be between 1 and 24")
        
        # Validate start time format
        start_time = self.schedule_start_time
        if start_time and not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', start_time):
            raise ConfigError("SCHEDULE_START_TIME must be in HH:MM format (24-hour)")
    
    @property
    def telegram_bot_token(self) -> str:
        """Get Telegram bot token."""
        return os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    @property
    def telegram_chat_id(self) -> str:
        """Get Telegram chat ID."""
        return os.getenv("TELEGRAM_CHAT_ID", "")
    
    @property
    def telegram_bot_username(self) -> str:
        """Get Telegram bot username."""
        return os.getenv("TELEGRAM_BOT_USERNAME", "")
    
    @property
    def ollama_host(self) -> str:
        """Get Ollama host URL."""
        return os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    @property
    def ollama_model(self) -> str:
        """Get Ollama model name."""
        return os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    
    @property
    def database_path(self) -> Path:
        """Get database file path."""
        db_dir = self.project_root / "data"
        db_dir.mkdir(exist_ok=True)
        return db_dir / "subscriptions_state.db"
    
    @property
    def youtube_channel_ids(self) -> list:
        """Get list of YouTube channel IDs (up to 100)."""
        channel_ids_str = os.getenv("YOUTUBE_CHANNEL_IDS", "")
        if not channel_ids_str:
            return []
        channels = [cid.strip() for cid in channel_ids_str.split(",") if cid.strip()]
        return channels[:self.MAX_CHANNELS]  # Limit to 100 channels
    
    @property
    def schedule_start_time(self) -> Optional[str]:
        """
        Get schedule start time in HH:MM format (24-hour).
        Returns None if not set (defaults to current time + 5 minutes).
        """
        return os.getenv("SCHEDULE_START_TIME", None)
    
    @property
    def schedule_frequency_hours(self) -> int:
        """
        Get schedule frequency in hours (1-24).
        Defaults to 6 hours if not set.
        """
        try:
            return int(os.getenv("SCHEDULE_FREQUENCY_HOURS", "6"))
        except ValueError:
            return 6
    
    def get_next_run_time(self) -> datetime:
        """
        Calculate the next run time based on schedule configuration.
        
        Returns:
            Next scheduled run time as datetime object.
        """
        now = datetime.now()
        
        if self.schedule_start_time:
            # Parse start time
            hours, minutes = map(int, self.schedule_start_time.split(":"))
            start_time_today = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            
            # If start time is today and has passed, schedule for tomorrow
            if start_time_today <= now:
                start_time_today += timedelta(days=1)
            
            return start_time_today
        else:
            # Default: current time + 5 minutes
            return now + timedelta(minutes=5)
    
    def get_all_config(self) -> dict:
        """Get all configuration as dictionary (masks sensitive values)."""
        return {
            "telegram_bot_token": "***" if self.telegram_bot_token else "",
            "telegram_chat_id": self.telegram_chat_id,
            "telegram_bot_username": self.telegram_bot_username,
            "ollama_host": self.ollama_host,
            "ollama_model": self.ollama_model,
            "database_path": str(self.database_path),
            "youtube_channel_ids": self.youtube_channel_ids,
            "channel_count": len(self.youtube_channel_ids),
            "max_channels": self.MAX_CHANNELS,
            "schedule_start_time": self.schedule_start_time or "Not set (defaults to now + 5 min)",
            "schedule_frequency_hours": self.schedule_frequency_hours,
            "next_run_time": self.get_next_run_time().strftime("%Y-%m-%d %H:%M:%S"),
            "project_root": str(self.project_root)
        }
    
    def print_config(self) -> None:
        """Print configuration (masking sensitive values)."""
        config = self.get_all_config()
        print("Configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")


def load_config(env_file: Optional[str] = None) -> Config:
    """
    Load and validate configuration.
    
    Args:
        env_file: Path to .env file. If None, uses default .env in project root.
        
    Returns:
        Config object with validated configuration.
        
    Raises:
        ConfigError: If configuration is invalid or missing required variables.
    """
    return Config(env_file)


if __name__ == "__main__":
    # Test configuration loading
    try:
        config = load_config()
        config.print_config()
        print("\nConfiguration loaded successfully!")
    except ConfigError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")