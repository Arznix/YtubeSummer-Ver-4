# Prerequisites Setup Guide

This guide will help you set up all prerequisites for the YouTube Summarizer pipeline.

## 1. Python Environment

### Python Version
- Python 3.8 or higher recommended
- Check your version: `python --version`

### Install Dependencies
```bash
pip install -r requirements.txt
```

## 2. Ollama Setup

### Install Ollama
1. Visit [https://ollama.com/download](https://ollama.com/download)
2. Download and install for your operating system
3. Start the Ollama service

### Pull Required Model
```bash
# Pull the Qwen 2.5 7B model
ollama pull qwen2.5:1.5b

# Verify installation
ollama list
```

### Test Ollama Connection
```bash
# Test if Ollama is running
curl http://localhost:11434/api/tags

# Test model availability
ollama run qwen2.5:1.5b "Hello, world!"
```

### Ollama Configuration
- Default host: `http://localhost:11434`
- Default model: `qwen2.5:1.5b`
- API documentation: [https://docs.ollama.com/api](https://docs.ollama.com/api)

## 3. Telegram Bot Setup

### Create Bot
1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Choose a name for your bot (e.g., "YouTube Summarizer Bot")
4. Choose a username ending with `bot` (e.g., "youtube_summary_bot")
5. Copy the bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Get Chat ID
1. Send any message to your new bot
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find your chat ID in the response:
   ```json
   {
     "result": [{
       "message": {
         "chat": {
           "id": 123456789,
           ...
         }
       }
     }]
   }
   ```

### Test Bot Connection
```bash
# Replace with your token and chat ID
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/sendMessage" \
  -d "chat_id=<YOUR_CHAT_ID>" \
  -d "text=Hello from YouTube Summarizer!"
```

## 4. YouTube Channel IDs

### Find Channel ID
Method 1: Using the helper script
```bash
python skills/youtube-rss-reader/scripts/find_channel_id.py @channelname
```

Method 2: Manual method
1. Go to the YouTube channel page
2. View page source (Ctrl+U)
3. Search for `channel_id=` in RSS feed link
4. Channel ID format: `UC-lHJZR3Gqxm24_Vd_AJ5Yw`

### Example Channel IDs
- Veritasium: `UCHnyfMqiRRG1u-2MsSQLbXA`
- 3Blue1Brown: `UCYO_jab_esuFRV4b17AJtAw`
- SmarterEveryDay: `UC6107grRIKm2yNs6Tycibdg`

## 5. Environment Configuration

### Create .env File
```bash
# Copy the example template
cp .env.example .env
```

### Edit .env File
```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b

# YouTube Channel IDs (comma-separated)
YOUTUBE_CHANNEL_IDS=UC-lHJZR3Gqxm24_Vd_AJ5Yw,UCHnyfMqiRRG1u-2MsSQLbXA
```

## 6. Verify Setup

### Run Setup Wizard
```bash
# Terminal wizard
python src/setup.py

# Browser-based setup (recommended)
python src/setup.py --web
```

### Run Tests
```bash
python test_agent.py

# Web setup tests
python -m pytest test_web_setup.py test_web_setup_api.py -v
```

### Test Individual Components

#### Test Ollama Connection
```python
from src.ollama_client import OllamaClient
client = OllamaClient()
print("Ollama available:", client.is_available())
```

#### Test Telegram Connection
```python
from src.mcp_server_notifier import TelegramMCPServer
server = TelegramMCPServer("YOUR_TOKEN", "YOUR_CHAT_ID")
print("Telegram connected:", server.test_connection())
```

#### Test YouTube RSS
```python
from src.mcp_server_youtube import YouTubeMCPServer
server = YouTubeMCPServer()
videos = server.fetch_latest_videos_from_rss("UCHnyfMqiRRG1u-2MsSQLbXA")
print(f"Found {len(videos)} videos")
```

## 7. Troubleshooting

### Common Issues

#### Ollama Not Starting
```bash
# Check if Ollama is running
ps aux | grep ollama

# Restart Ollama
ollama serve

# Check logs
journalctl -u ollama
```

#### Telegram Bot Not Responding
- Verify bot token is correct
- Ensure you've sent at least one message to the bot
- Check chat ID is correct
- Verify internet connection

#### YouTube RSS Feed Issues
- Channel may be invalid or private
- RSS feed may be disabled
- Check network connectivity
- Try with a known working channel ID

#### Python Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Check Python path
python -c "import sys; print(sys.path)"
```

### Debug Mode
Enable debug logging by setting in `.env`:
```env
LOG_LEVEL=DEBUG
```

## 8. Security Notes

### Token Security
- Never commit `.env` file to version control
- Keep bot tokens secure
- Rotate tokens if compromised

### Network Security
- Ollama runs locally (no external calls)
- Telegram API uses HTTPS
- YouTube RSS is public data

### Web Setup Security
- Server binds to localhost only (127.0.0.1)
- Auth token required for all API requests
- CSRF protection for all POST requests
- Bot token masked in browser UI
- All requests logged to `web_setup.log`

## 9. Next Steps

Once prerequisites are set up:
1. Run the setup wizard: `python src/setup.py` or `python src/setup.py --web`
2. Test the pipeline: `python src/agent_orchestrator.py --once`
3. Set up as background service: `python src/agent_orchestrator.py`

## 10. Resources

- [Ollama Documentation](https://docs.ollama.com/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [YouTube RSS Feeds](https://www.youtube.com/rss)
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)