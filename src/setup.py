import os
import sys
from pathlib import Path
from typing import Optional, List
import re
import requests

from dotenv import load_dotenv, set_key


class SetupError(Exception):
    pass


class SetupWizard:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(self.project_root / "src"))

        from config import get_config_dir

        self.config_dir = get_config_dir()
        self.env_file = self.config_dir / ".env"
        self.env_example = self.project_root / ".env.example"

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._create_env_example()

    def _create_env_example(self) -> None:
        if not self.env_example.exists():
            example_content = """# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b

# YouTube Channel IDs (comma-separated)
YOUTUBE_CHANNEL_IDS=channel_id_1,channel_id_2

# Optional: Database path (default: data/subscriptions_state.db)
# DATABASE_PATH=data/subscriptions_state.db

# Rate limiting: random delay between YOUTUBE_REQUEST_DELAY_MIN and YOUTUBE_REQUEST_DELAY_MAX
# seconds between YouTube requests to avoid bot detection patterns (default: 60–240)
# Proxies are used as a fallback only when rate limiting fails
# YOUTUBE_REQUEST_DELAY_MIN=60
# YOUTUBE_REQUEST_DELAY_MAX=240

# Proxy rotation: comma-separated list of proxy URLs for IP rotation
# Supports http://, https://, socks4://, socks5://
# YOUTUBE_PROXY_LIST=http://proxy1:8080,http://proxy2:8080
"""
            self.env_example.write_text(example_content)
            print(f"Created {self.env_example}")

    def clear_screen(self) -> None:
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self) -> None:
        self.clear_screen()
        print("=" * 60)
        print("YouTube Summarizer Setup Wizard")
        print("=" * 60)
        print()

    def prompt_input(self, prompt: str, default: Optional[str] = None, required: bool = True) -> str:
        while True:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    user_input = default
            else:
                user_input = input(f"{prompt}: ").strip()
            if user_input or not required:
                return user_input
            print("This field is required. Please enter a value.")

    def validate_telegram_token(self, token: str) -> bool:
        return bool(re.match(r'^\d+:[A-Za-z0-9_-]+$', token))

    def validate_ollama_host(self, host: str) -> bool:
        return host.startswith(("http://", "https://"))

    def extract_channel_id_from_url(self, url: str) -> Optional[str]:
        url = url.strip()
        channel_match = re.search(r'youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})', url)
        if channel_match:
            return channel_match.group(1)
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            patterns = [
                r'"channelId":"(UC[a-zA-Z0-9_-]{22})"',
                r'"externalId":"(UC[a-zA-Z0-9_-]{22})"',
                r'channel_id=(UC[a-zA-Z0-9_-]{22})',
                r'/channel/(UC[a-zA-Z0-9_-]{22})',
            ]
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    return match.group(1)
            rss_match = re.search(r'rss\.youtube\.com.*channel_id=(UC[a-zA-Z0-9_-]{22})', response.text)
            if rss_match:
                return rss_match.group(1)
            return None
        except Exception as e:
            print(f"Error fetching URL: {e}")
            return None

    def is_valid_channel_id(self, channel_id: str) -> bool:
        return bool(re.match(r'^UC[a-zA-Z0-9_-]{22}$', channel_id))

    def setup_telegram(self) -> dict:
        print("\n--- Telegram Configuration ---")
        print("You need a Telegram bot token and chat ID.")
        print()
        print("How to create a Telegram bot:")
        print("  1. Open Telegram and search for @BotFather")
        print("  2. Send /newbot and follow the instructions")
        print("  3. Copy the bot token (format: 123456789:ABCdefGHIjklMNOpqrSTUvwxYZ)")
        print("  4. Send a message to your bot, then visit:")
        print("     https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates")
        print("     to find your chat ID (a number like: 123456789)")
        print()
        while True:
            token = self.prompt_input("Enter Telegram bot token")
            if self.validate_telegram_token(token):
                print("  [OK] Valid bot token format")
                break
            print("  [ERROR] Invalid token format!")
            print("  Expected format: 123456789:ABCdefGHIjklMNOpqrSTUvwxYZ")
            print()
        while True:
            chat_id = self.prompt_input("Enter Telegram chat ID")
            if chat_id.isdigit():
                print("  [OK] Valid chat ID format")
                break
            print("  [ERROR] Chat ID must be a number!")
            print()
        return {"TELEGRAM_BOT_TOKEN": token, "TELEGRAM_CHAT_ID": chat_id}

    def setup_ollama(self) -> dict:
        print("\n--- Ollama Configuration ---")
        print("Ollama should be installed and running locally.")
        print()
        print("Default settings:")
        print("  - Host: http://localhost:11434")
        print("  - Model: qwen2.5:1.5b (recommended for speed)")
        print("  - Alternative: qwen2.5:7b (better quality but slower)")
        print()
        while True:
            host = self.prompt_input("Enter Ollama host URL", "http://localhost:11434")
            if self.validate_ollama_host(host):
                print("  [OK] Valid Ollama host URL")
                break
            print("  [ERROR] Invalid URL format!")
            print()
        while True:
            model = self.prompt_input("Enter Ollama model name", "qwen2.5:1.5b")
            if model.strip():
                print(f"  [OK] Model set to: {model}")
                break
            print("  [ERROR] Model name cannot be empty!")
            print()
        return {"OLLAMA_HOST": host, "OLLAMA_MODEL": model}

    def setup_youtube_channels(self) -> dict:
        print("\n--- YouTube Channel Configuration ---")
        print("Enter YouTube channel IDs or URLs (comma-separated).")
        print("You can add up to 100 channels.")
        print()
        print("Supported input formats:")
        print("  - Channel URL: https://www.youtube.com/@ChannelHandle")
        print("  - Channel URL: https://www.youtube.com/c/ChannelName")
        print("  - Channel URL: https://www.youtube.com/channel/UCxxxxxx")
        print("  - Channel ID directly: UCxxxxxx (starts with 'UC', 24 characters)")
        print()
        channel_input = self.prompt_input("Enter YouTube channel IDs or URLs (comma-separated)", required=False)
        if channel_input:
            items = [item.strip() for item in channel_input.split(",") if item.strip()]
            channel_ids = []
            errors = []
            for item in items:
                if item.startswith(("http://", "https://", "www.")):
                    print(f"\n  Processing URL: {item}")
                    if not re.match(r'https?://(www\.)?(youtube\.com|youtu\.be)/', item):
                        print("  [ERROR] Not a valid YouTube URL!")
                        errors.append(item)
                        continue
                    print("  [OK] Valid YouTube URL format")
                    print("  Extracting channel ID...")
                    channel_id = self.extract_channel_id_from_url(item)
                    if channel_id:
                        print(f"  [SUCCESS] Channel ID extracted: {channel_id}")
                        if self.is_valid_channel_id(channel_id):
                            print(f"  [OK] Valid channel ID format")
                        channel_ids.append(channel_id)
                    else:
                        print(f"  [ERROR] Could not extract channel ID from this URL!")
                        errors.append(item)
                elif self.is_valid_channel_id(item):
                    print(f"  [OK] Valid channel ID: {item}")
                    channel_ids.append(item)
                elif item.startswith("UC"):
                    print(f"  [WARNING] Invalid channel ID format: {item}")
                    errors.append(item)
                else:
                    print(f"  [ERROR] Invalid input: {item}")
                    errors.append(item)
            print()
            if errors:
                print(f"  [SUMMARY] {len(errors)} item(s) had errors and were skipped")
            if len(channel_ids) > 100:
                print(f"  [WARNING] You entered {len(channel_ids)} channels. Limiting to 100.")
                channel_ids = channel_ids[:100]
            seen = set()
            unique_channel_ids = []
            for cid in channel_ids:
                if cid not in seen:
                    seen.add(cid)
                    unique_channel_ids.append(cid)
            if unique_channel_ids:
                print(f"  [OK] Total channels configured: {len(unique_channel_ids)}")
                for i, cid in enumerate(unique_channel_ids, 1):
                    print(f"    {i}. {cid}")
            else:
                print("  [WARNING] No valid channels were added!")
            channel_ids_str = ",".join(unique_channel_ids)
        else:
            channel_ids_str = ""
            print("  [INFO] No channels entered. You can add them later.")
        return {"YOUTUBE_CHANNEL_IDS": channel_ids_str}

    def setup_youtube_api_key(self) -> dict:
        print("\n--- YouTube Data API Key (optional) ---")
        print("Get a free key at https://console.cloud.google.com/apis/library/youtube.googleapis.com")
        print("If provided, the program uses the official YouTube API (more reliable).")
        print("If left blank, the program falls back to HTML scraping.")
        print()
        key = self.prompt_input("YouTube Data API Key", required=False)
        print()
        if key:
            print("  [OK] API key set")
        else:
            print("  [INFO] No API key — will use scraping fallback")
        return {"YOUTUBE_API_KEY": key} if key else {}

    def setup_scheduling(self) -> dict:
        print("\n--- Scheduling Configuration ---")
        print("Configure how often to check for new videos.")
        print()
        print("Start Time Configuration:")
        print("  - Format: HH:MM (24-hour format)")
        print("  - Press Enter to start 5 minutes after setup completes")
        print()
        start_time = None
        while True:
            start_time_input = self.prompt_input("Enter start time (HH:MM format, 24-hour)", required=False)
            if not start_time_input:
                print("  [INFO] No start time set. Scheduler will start 5 minutes after launch.")
                break
            if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', start_time_input):
                print("  [ERROR] Invalid time format!")
                continue
            print(f"  [OK] Start time set to: {start_time_input}")
            start_time = start_time_input
            break
        print()
        print("Check Frequency Configuration:")
        print("  - Valid range: 1-24 hours")
        print()
        frequency = None
        while True:
            frequency_input = self.prompt_input("Enter check frequency in hours (1-24)", "6")
            try:
                frequency = int(frequency_input)
            except ValueError:
                print("  [ERROR] Invalid input!")
                continue
            if frequency < 1 or frequency > 24:
                print("  [ERROR] Frequency must be between 1 and 24!")
                continue
            print(f"  [OK] Check frequency set to: every {frequency} hour(s)")
            break
        config = {"SCHEDULE_FREQUENCY_HOURS": str(frequency)}
        if start_time:
            config["SCHEDULE_START_TIME"] = start_time
        return config

    def save_configuration(self, config: dict) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)

        from config import Config as Cfg

        bot_token = config.pop("TELEGRAM_BOT_TOKEN", None)
        chat_id = config.pop("TELEGRAM_CHAT_ID", None)

        if bot_token and chat_id:
            Cfg.store_credentials(bot_token, chat_id)

        for key, value in config.items():
            set_key(str(self.env_file), key, value)

        print(f"\nConfiguration saved to {self.env_file}")
        print("Sensitive credentials (bot token, chat ID) stored in OS keychain.")

    def test_configuration(self) -> bool:
        print("\n--- Testing Configuration ---")
        try:
            sys.path.insert(0, str(self.project_root / "src"))
            from config import load_config

            config = load_config(str(self.env_file))
            print("[OK] Configuration loaded successfully!")

            print("\nTesting Ollama connection...")
            try:
                response = requests.get(f"{config.ollama_host}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name") for m in models]
                    if config.ollama_model in model_names:
                        print(f"[OK] Ollama model '{config.ollama_model}' found")
                    else:
                        print(f"[WARNING] Ollama model '{config.ollama_model}' not found")
                        print(f"  Run: ollama pull {config.ollama_model}")
                else:
                    print("[ERROR] Cannot connect to Ollama")
            except requests.exceptions.RequestException as e:
                print(f"[ERROR] Ollama connection failed: {e}")

            return True
        except Exception as e:
            print(f"[ERROR] Configuration test failed: {e}")
            return False

    def run(self) -> None:
        self.print_header()
        print("This wizard will help you configure the YouTube Summarizer.")
        print("Press Enter to accept default values (shown in brackets).")
        print()

        if self.env_file.exists():
            response = input(f"Configuration already exists at {self.env_file}. Overwrite? (y/N): ").strip().lower()
            if response != 'y':
                print("Setup cancelled.")
                return

        config = {}
        config.update(self.setup_telegram())
        config.update(self.setup_ollama())
        config.update(self.setup_youtube_channels())
        config.update(self.setup_youtube_api_key())
        config.update(self.setup_scheduling())
        self.save_configuration(config)

        if self.test_configuration():
            print("\n" + "=" * 60)
            print("Setup completed successfully!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Ensure Ollama is running with the configured model")
            print("2. Run: python src/agent_orchestrator.py")
            print("3. Or run once: python src/agent_orchestrator.py --once")
        else:
            print("\nSetup completed with warnings. Please check the configuration.")


def main():
    try:
        if "--web" in sys.argv:
            from web_setup import WebSetupServer
            port = 8080
            for i, arg in enumerate(sys.argv):
                if arg == "--port" and i + 1 < len(sys.argv):
                    try:
                        port = int(sys.argv[i + 1])
                    except ValueError:
                        pass
            server = WebSetupServer(port=port)
            server.serve()
        else:
            wizard = SetupWizard()
            wizard.run()
    except KeyboardInterrupt:
        print("\nSetup cancelled by user.")
    except Exception as e:
        print(f"Setup error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
