import os
import sys
from pathlib import Path
from typing import Optional, List
import re
import requests

from dotenv import load_dotenv, set_key


class SetupError(Exception):
    """Setup error exception."""
    pass


class SetupWizard:
    """Interactive setup wizard for YouTube Summarizer."""
    
    def __init__(self):
        """Initialize the setup wizard."""
        self.project_root = Path(__file__).parent.parent
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / ".env.example"
        
        # Ensure .env.example exists
        self._create_env_example()
    
    def _create_env_example(self) -> None:
        """Create .env.example file if it doesn't exist."""
        if not self.env_example.exists():
            example_content = """# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# YouTube Channel IDs (comma-separated)
YOUTUBE_CHANNEL_IDS=channel_id_1,channel_id_2

# Optional: Database path (default: data/subscriptions_state.db)
# DATABASE_PATH=data/subscriptions_state.db
"""
            self.env_example.write_text(example_content)
            print(f"Created {self.env_example}")
    
    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self) -> None:
        """Print setup wizard header."""
        self.clear_screen()
        print("=" * 60)
        print("YouTube Summarizer Setup Wizard")
        print("=" * 60)
        print()
    
    def prompt_input(self, prompt: str, default: Optional[str] = None, required: bool = True) -> str:
        """
        Prompt user for input with optional default value.
        
        Args:
            prompt: Input prompt message
            default: Default value if user presses Enter
            required: Whether input is required
            
        Returns:
            User input or default value
        """
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
        """
        Validate Telegram bot token format.
        
        Args:
            token: Telegram bot token
            
        Returns:
            True if valid, False otherwise
        """
        return bool(re.match(r'^\d+:[A-Za-z0-9_-]+$', token))
    
    def validate_ollama_host(self, host: str) -> bool:
        """
        Validate Ollama host URL.
        
        Args:
            host: Ollama host URL
            
        Returns:
            True if valid, False otherwise
        """
        return host.startswith(("http://", "https://"))
    
    def extract_channel_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract YouTube channel ID from a URL.
        
        Supports formats:
        - https://www.youtube.com/channel/UCxxxxxx
        - https://www.youtube.com/c/ChannelName
        - https://www.youtube.com/@ChannelHandle
        - https://youtube.com/channel/UCxxxxxx
        
        Args:
            url: YouTube channel URL
            
        Returns:
            Channel ID or None if extraction fails
        """
        url = url.strip()
        
        # Pattern 1: Direct channel ID URL (e.g., /channel/UCxxxxxx)
        channel_match = re.search(r'youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})', url)
        if channel_match:
            return channel_match.group(1)
        
        # Pattern 2: Custom URL or handle - need to scrape
        try:
            # Add headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Look for channel ID in page source
            # YouTube embeds channel ID in various places
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
            
            # Try to find via RSS feed link
            rss_match = re.search(r'rss\.youtube\.com.*channel_id=(UC[a-zA-Z0-9_-]{22})', response.text)
            if rss_match:
                return rss_match.group(1)
            
            return None
            
        except Exception as e:
            print(f"Error fetching URL: {e}")
            return None
    
    def is_valid_channel_id(self, channel_id: str) -> bool:
        """
        Validate YouTube channel ID format.
        
        Args:
            channel_id: Channel ID to validate
            
        Returns:
            True if valid format, False otherwise
        """
        return bool(re.match(r'^UC[a-zA-Z0-9_-]{22}$', channel_id))
    
    def setup_telegram(self) -> dict:
        """Setup Telegram configuration."""
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
        
        # Get bot token
        while True:
            token = self.prompt_input("Enter Telegram bot token")
            if self.validate_telegram_token(token):
                print("  [OK] Valid bot token format")
                break
            print("  [ERROR] Invalid token format!")
            print("  Expected format: 123456789:ABCdefGHIjklMNOpqrSTUvwxYZ")
            print("  - Must start with numbers")
            print("  - Must contain a colon (:)")
            print("  - Must contain letters, numbers, underscores, or hyphens after colon")
            print()
        
        # Get chat ID
        while True:
            chat_id = self.prompt_input("Enter Telegram chat ID")
            if chat_id.isdigit():
                print("  [OK] Valid chat ID format")
                break
            print("  [ERROR] Chat ID must be a number!")
            print("  - Only digits are allowed (e.g., 6758055228)")
            print("  - No spaces, letters, or special characters")
            print()
        
        return {
            "TELEGRAM_BOT_TOKEN": token,
            "TELEGRAM_CHAT_ID": chat_id
        }
    
    def setup_ollama(self) -> dict:
        """Setup Ollama configuration."""
        print("\n--- Ollama Configuration ---")
        print("Ollama should be installed and running locally.")
        print()
        print("Default settings:")
        print("  - Host: http://localhost:11434")
        print("  - Model: qwen2.5-coder:1.5b (recommended for speed)")
        print("  - Alternative: qwen2.5:7b (better quality but slower)")
        print()
        
        # Get Ollama host
        while True:
            host = self.prompt_input("Enter Ollama host URL", "http://localhost:11434")
            if self.validate_ollama_host(host):
                print("  [OK] Valid Ollama host URL")
                break
            print("  [ERROR] Invalid URL format!")
            print("  - Must start with http:// or https://")
            print("  - Example: http://localhost:11434")
            print()
        
        # Get model name
        while True:
            model = self.prompt_input("Enter Ollama model name", "qwen2.5-coder:1.5b")
            if model.strip():
                print(f"  [OK] Model set to: {model}")
                break
            print("  [ERROR] Model name cannot be empty!")
            print()
        
        return {
            "OLLAMA_HOST": host,
            "OLLAMA_MODEL": model
        }
    
    def setup_youtube_channels(self) -> dict:
        """Setup YouTube channel configuration (up to 100 channels)."""
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
        print("Examples:")
        print("  - https://www.youtube.com/@veritasium")
        print("  - UCin0m13qWv3-051xlWlHamA")
        print("  - Multiple: URL1,URL2,ChannelID3")
        print()
        
        channel_input = self.prompt_input(
            "Enter YouTube channel IDs or URLs (comma-separated)",
            required=False
        )
        
        # Clean up input
        if channel_input:
            items = [item.strip() for item in channel_input.split(",") if item.strip()]
            channel_ids = []
            errors = []
            
            for item in items:
                # Check if it's a URL or a channel ID
                if item.startswith(("http://", "https://", "www.")):
                    print(f"\n  Processing URL: {item}")
                    
                    # Validate URL format
                    if not re.match(r'https?://(www\.)?(youtube\.com|youtu\.be)/', item):
                        print("  [ERROR] Not a valid YouTube URL!")
                        print("  - Must be a YouTube URL (youtube.com or youtu.be)")
                        print("  - Example: https://www.youtube.com/@veritasium")
                        errors.append(item)
                        continue
                    
                    print("  [OK] Valid YouTube URL format")
                    print("  Extracting channel ID...")
                    
                    channel_id = self.extract_channel_id_from_url(item)
                    if channel_id:
                        print(f"  [SUCCESS] Channel ID extracted: {channel_id}")
                        if self.is_valid_channel_id(channel_id):
                            print(f"  [OK] Valid channel ID format (starts with 'UC', 24 characters)")
                            channel_ids.append(channel_id)
                        else:
                            print(f"  [WARNING] Extracted ID doesn't match expected format")
                            channel_ids.append(channel_id)
                    else:
                        print(f"  [ERROR] Could not extract channel ID from this URL!")
                        print("  Possible reasons:")
                        print("  - URL does not point to a YouTube channel")
                        print("  - Channel may not exist")
                        print("  - Network error occurred")
                        print("  Please enter the channel ID manually (starts with 'UC')")
                        errors.append(item)
                
                elif self.is_valid_channel_id(item):
                    # It's already a valid channel ID
                    print(f"  [OK] Valid channel ID: {item}")
                    channel_ids.append(item)
                
                elif item.startswith("UC"):
                    # Looks like a channel ID but wrong format
                    print(f"  [WARNING] Looks like a channel ID but invalid format: {item}")
                    print(f"  - Channel IDs must be exactly 24 characters")
                    print(f"  - Your input: {len(item)} characters")
                    print(f"  Skipping this entry.")
                    errors.append(item)
                
                else:
                    print(f"  [ERROR] Invalid input: {item}")
                    print("  - If this is a URL, it must be a YouTube URL")
                    print("  - If this is a channel ID, it must start with 'UC' and be 24 characters")
                    print("  - Example: https://www.youtube.com/@veritasium")
                    print("  - Example: UCin0m13qWv3-051xlWlHamA")
                    errors.append(item)
            
            # Show summary
            print()
            if errors:
                print(f"  [SUMMARY] {len(errors)} item(s) had errors and were skipped")
            
            # Limit to 100 channels
            if len(channel_ids) > 100:
                print(f"  [WARNING] You entered {len(channel_ids)} channels. Limiting to 100.")
                channel_ids = channel_ids[:100]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_channel_ids = []
            for cid in channel_ids:
                if cid not in seen:
                    seen.add(cid)
                    unique_channel_ids.append(cid)
            
            if len(unique_channel_ids) < len(channel_ids):
                print(f"  [INFO] Removed {len(channel_ids) - len(unique_channel_ids)} duplicate(s)")
            
            if unique_channel_ids:
                print(f"  [OK] Total channels configured: {len(unique_channel_ids)}")
                print()
                print("  Configured channels:")
                for i, cid in enumerate(unique_channel_ids, 1):
                    print(f"    {i}. {cid}")
            else:
                print("  [WARNING] No valid channels were added!")
            
            channel_ids_str = ",".join(unique_channel_ids)
        else:
            channel_ids_str = ""
            print("  [INFO] No channels entered. You can add them later.")
        
        return {
            "YOUTUBE_CHANNEL_IDS": channel_ids_str
        }
    
    def setup_scheduling(self) -> dict:
        """Setup scheduling configuration."""
        print("\n--- Scheduling Configuration ---")
        print("Configure how often to check for new videos.")
        print()
        
        # Get start time
        print("Start Time Configuration:")
        print("  - Format: HH:MM (24-hour format)")
        print("  - Examples: 06:30 (6:30 AM), 14:00 (2:00 PM), 20:30 (8:30 PM)")
        print("  - Valid hours: 00-23")
        print("  - Valid minutes: 00-59")
        print("  - Press Enter to start 5 minutes after setup completes")
        print()
        print("  Examples:")
        print("    06:30  = Start at 6:30 AM daily")
        print("    12:00  = Start at noon daily")
        print("    18:45  = Start at 6:45 PM daily")
        print("    23:00  = Start at 11:00 PM daily")
        print()
        
        start_time = None
        while True:
            start_time_input = self.prompt_input(
                "Enter start time (HH:MM format, 24-hour)",
                required=False
            )
            
            if not start_time_input:
                print("  [INFO] No start time set. Scheduler will start 5 minutes after launch.")
                break
            
            # Validate start time format
            if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', start_time_input):
                print("  [ERROR] Invalid time format!")
                print("  - Must be in HH:MM format (24-hour)")
                print("  - Hours: 00-23")
                print("  - Minutes: 00-59")
                print("  - Examples: 06:30, 14:00, 20:30")
                print()
                continue
            
            # Additional validation
            hours, minutes = start_time_input.split(":")
            hours = int(hours)
            minutes = int(minutes)
            
            if hours < 0 or hours > 23:
                print("  [ERROR] Hours must be between 00 and 23!")
                continue
            
            if minutes < 0 or minutes > 59:
                print("  [ERROR] Minutes must be between 00 and 59!")
                continue
            
            print(f"  [OK] Start time set to: {start_time_input}")
            start_time = start_time_input
            break
        
        # Get frequency
        print()
        print("Check Frequency Configuration:")
        print("  - How often to check for new videos")
        print("  - Valid range: 1-24 hours")
        print("  - Example: 6 means check every 6 hours")
        print()
        print("  Common frequencies:")
        print("    1  = Check every hour (most frequent)")
        print("    2  = Check every 2 hours")
        print("    4  = Check every 4 hours")
        print("    6  = Check every 6 hours (recommended)")
        print("    8  = Check every 8 hours")
        print("    12 = Check every 12 hours (twice daily)")
        print("    24 = Check once daily")
        print()
        
        frequency = None
        while True:
            frequency_input = self.prompt_input(
                "Enter check frequency in hours (1-24)",
                "6"
            )
            
            # Validate frequency is a number
            try:
                frequency = int(frequency_input)
            except ValueError:
                print("  [ERROR] Invalid input!")
                print("  - Must be a whole number")
                print("  - Example: 6")
                print()
                continue
            
            # Validate frequency range
            if frequency < 1:
                print("  [ERROR] Frequency too low!")
                print("  - Minimum is 1 hour")
                print("  - Use 1 for hourly checks")
                print()
                continue
            
            if frequency > 24:
                print("  [ERROR] Frequency too high!")
                print("  - Maximum is 24 hours")
                print("  - Use 24 for once-daily checks")
                print()
                continue
            
            print(f"  [OK] Check frequency set to: every {frequency} hour(s)")
            break
        
        config = {
            "SCHEDULE_FREQUENCY_HOURS": str(frequency)
        }
        
        if start_time:
            config["SCHEDULE_START_TIME"] = start_time
        
        return config
    
    def save_configuration(self, config: dict) -> None:
        """
        Save configuration to .env file.
        
        Args:
            config: Configuration dictionary
        """
        # Create or update .env file
        for key, value in config.items():
            set_key(str(self.env_file), key, value)
        
        print(f"\nConfiguration saved to {self.env_file}")
    
    def test_configuration(self) -> bool:
        """Test the configuration by loading it."""
        print("\n--- Testing Configuration ---")
        
        try:
            # Import here to avoid circular imports
            sys.path.insert(0, str(self.project_root / "src"))
            from config import load_config
            
            config = load_config(str(self.env_file))
            print("[OK] Configuration loaded successfully!")
            
            # Test Ollama connection
            print("\nTesting Ollama connection...")
            import requests
            try:
                response = requests.get(f"{config.ollama_host}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name") for m in models]
                    if config.ollama_model in model_names:
                        print(f"[OK] Ollama model '{config.ollama_model}' found")
                    else:
                        print(f"[WARNING] Ollama model '{config.ollama_model}' not found")
                        print(f"  Available models: {model_names}")
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
        """Run the setup wizard."""
        self.print_header()
        
        print("This wizard will help you configure the YouTube Summarizer.")
        print("Press Enter to accept default values (shown in brackets).")
        print()
        
        # Check if .env already exists
        if self.env_file.exists():
            response = input("Configuration file already exists. Overwrite? (y/N): ").strip().lower()
            if response != 'y':
                print("Setup cancelled.")
                return
        
        # Gather configuration
        config = {}
        
        # Telegram setup
        config.update(self.setup_telegram())
        
        # Ollama setup
        config.update(self.setup_ollama())
        
        # YouTube channels setup
        config.update(self.setup_youtube_channels())
        
        # Scheduling setup
        config.update(self.setup_scheduling())
        
        # Save configuration
        self.save_configuration(config)
        
        # Test configuration
        if self.test_configuration():
            print("\n" + "=" * 60)
            print("Setup completed successfully!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Ensure Ollama is running with the configured model")
            print("2. Run the orchestrator: python src/agent_orchestrator.py")
            print("3. Or run once: python src/agent_orchestrator.py --once")
            print("\nScheduling:")
            print("- The scheduler will start at the configured time")
            print("- Videos will be checked at the configured frequency")
            print("- All channels are checked together on the same schedule")
        else:
            print("\nSetup completed with warnings. Please check the configuration.")


def main():
    """Main entry point for setup wizard."""
    try:
        wizard = SetupWizard()
        wizard.run()
    except KeyboardInterrupt:
        print("\nSetup cancelled by user.")
    except Exception as e:
        print(f"Setup error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()