# YouTube Summarizer

A locally hosted, privacy-focused YouTube subscription summarizer that monitors your YouTube subscriptions via RSS feeds, extracts transcripts, generates AI-powered summaries using Ollama/Qwen, and delivers them to your Telegram.

## Features

- **Privacy-First**: All processing happens locally - no data sent to external AI services
- **Three-Way Video Fetch**: Official YouTube Data API v3 → RSS feed → HTML page scraping fallback
- **Local AI Summarization**: Uses Ollama with Qwen 2.5 models
- **Telegram Notifications**: Delivers formatted summaries directly to your chat
- **State Management**: SQLite database tracks processed videos
- **Smart Scheduling**: Configurable start time and frequency (1-24 hours)
- **Multi-Channel Support**: Monitor up to 100 YouTube channels
- **Modular Architecture**: Agent Skills pattern for reusability

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    YouTube Summarizer Pipeline                    │
├──────────────────────────────────────────────────────────────────┤
│  YouTube Data API v3 / RSS / Scrape  →  Transcript Extraction   │
│         ↓                                  ↓                    │
│  State Manager  →  Agent Orchestrator  →  Ollama/Qwen Summary   │
│                                              ↓                  │
│                                       Telegram Notification    │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Prerequisites
- Python 3.8+
- Ollama with qwen2.5:1.5b model (see setup below)
- Telegram bot token and chat ID
- YouTube channel IDs
- (Optional) YouTube Data API v3 key for reliable video fetching

See [PREREQUISITES.md](PREREQUISITES.md) for detailed setup instructions.

#### Start Ollama

Ollama must be running **before** you launch the program. It is not started automatically.

```bash
# Start the Ollama server
ollama serve

# In a separate terminal, pull the required model
ollama pull qwen2.5:1.5b

# Verify Ollama is reachable
curl http://localhost:11434/api/tags
```

If the `curl` command returns a JSON list of models, Ollama is running. If it says `Connection refused`, Ollama is not running — check that `ollama serve` completed without errors.

> `qwen2.5:1.5b` is the default model. You can use **any** local LLM supported by Ollama (e.g., `llama3`, `mistral`, `gemma`). Set the model name in `.env` with `OLLAMA_MODEL=your-model-name`.

> The default `OLLAMA_HOST=http://localhost:11434` in `.env` must match where Ollama is listening. Change it if Ollama is on a different machine or port.

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/Arznix/YtubeSummer-Ver-4.git
cd YtubeSummer-Ver-4
```

Install dependencies. On some systems you cannot run `pip install` directly. If you get errors, create and activate a virtual environment first:

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> You must activate the virtual environment every time you open a new terminal before running the program. When activated, you should see `(venv)` in your terminal prompt.

```bash
# Run setup wizard
python src/setup.py           # Terminal wizard
python src/setup.py --web     # Browser-based setup (recommended)
                              # The browser will be launched by the python code
                              # but it will take a while to initialize so be patient.
```

### 3. Configuration

You can also use the browser based interface described in the file "browser_setup.md". It uses a graphic interface to guide you through the setup and you avoid having to do the sets in this section.

Copy `.env.example` to `.env` and fill in your credentials:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b

# YouTube Channel IDs (comma-separated, up to 100 channels)
YOUTUBE_CHANNEL_IDS=channel_id_1,channel_id_2,channel_id_3

# YouTube Data API v3 Key (optional, but recommended for reliability)
# Get one free at: https://console.cloud.google.com/apis/library/youtube.googleapis.com
# Free tier: 10,000 quota units/day (~10,000 requests to playlistItems.list).
# With 6-hour checks and 2 videos per channel, a single channel uses ~4 requests/day.
# YOUTUBE_API_KEY=AIzaSy...

# Scheduling Configuration
# Start time in HH:MM format (24-hour), e.g., 06:30 for 6:30 AM
# If not set, defaults to current time + 5 minutes
SCHEDULE_START_TIME=06:30

# How often to check (1-24 hours)
SCHEDULE_FREQUENCY_HOURS=6
```

### 4. Usage

```bash
# Run once to process new videos
python src/agent_orchestrator.py --once

# Run with configured schedule (uses SCHEDULE_START_TIME and SCHEDULE_FREQUENCY_HOURS)
python src/agent_orchestrator.py

# Run with legacy interval (overrides config)
python src/agent_orchestrator.py --interval 60

# Check status and next run time
python src/agent_orchestrator.py --status
```

#### Scheduling Options

- **Start Time**: Set `SCHEDULE_START_TIME` to a specific time (e.g., `06:30`) to start checking at that time daily
- **Frequency**: Set `SCHEDULE_FREQUENCY_HOURS` to control how often to check (1-24 hours)
- **Default**: If no start time is set, the scheduler starts 5 minutes after launch
- **All channels are checked together** on the same schedule

## Project Structure

```
YtubeSummer-Ver-4/
├── src/                          # Source code
│   ├── config.py                # Configuration management
│   ├── state_manager.py         # SQLite state tracking
│   ├── mcp_server_youtube.py    # YouTube RSS & transcripts
│   ├── ollama_client.py         # Ollama API client
│   ├── mcp_server_notifier.py   # Telegram notifications
│   ├── agent_orchestrator.py    # Main application logic
│   ├── setup.py                 # Interactive setup wizard
│   └── web_setup.py             # Browser-based setup server
├── skills/                       # Agent Skills (reusable components)
│   ├── youtube-rss-reader/      # YouTube RSS parsing skill
│   └── telegram-notifier/       # Telegram notification skill
├── .env.example                 # Configuration template
├── requirements.txt             # Python dependencies
├── test_agent.py                # Automated tests
├── PREREQUISITES.md             # Setup guide
└── README.md                    # This file
```

## Agent Skills

This project implements the Agent Skills pattern for modular, reusable components:

### YouTube RSS Reader Skill
- Fetches videos via three methods: YouTube Data API v3 → RSS feed → HTML scraping
- Derives uploads playlist ID (UU) from channel ID (UC)
- Extracts video metadata, titles, thumbnails, publish dates
- Rate-limited with random jitter (60-240s) to avoid blocking

### Telegram Notifier Skill
- Send formatted messages
- Support Markdown/HTML formatting
- Document and photo sending

See `skills/*/SKILL.md` for detailed documentation.

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Yes | Your Telegram chat ID |
| `TELEGRAM_BOT_USERNAME` | No | Your Telegram bot username (e.g., @mybot) |
| `OLLAMA_HOST` | Yes | Ollama server URL (default: http://localhost:11434) |
| `OLLAMA_MODEL` | No | Model name (default: qwen2.5:1.5b) |
| `YOUTUBE_CHANNEL_IDS` | Yes | Comma-separated YouTube channel IDs (up to 100) |
| `YOUTUBE_API_KEY` | No | YouTube Data API v3 key. Free tier: 10,000 quota units/day |
| `SCHEDULE_START_TIME` | No | Start time in HH:MM format (24-hour). Defaults to now + 5 min |
| `SCHEDULE_FREQUENCY_HOURS` | No | Check frequency in hours (1-24, default: 6) |
| `YOUTUBE_REQUEST_DELAY_MIN` | No | Minimum seconds between YouTube requests (default: 60) |
| `YOUTUBE_REQUEST_DELAY_MAX` | No | Maximum seconds between YouTube requests for random jitter (default: 240) |
| `YOUTUBE_PROXY_LIST` | No | Comma-separated proxy URLs, used as fallback when rate limiting fails |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

### Scheduling Configuration

The scheduler supports flexible scheduling options:

- **Start Time**: Set a specific time to start checking (e.g., `06:30` for 6:30 AM)
- **Frequency**: How often to check for new videos (1-24 hours)
- **Default Behavior**: If no start time is set, the scheduler starts 5 minutes after launch
- **All channels are checked together** on the same schedule

Example configurations:
```env
# Check every 6 hours, starting at 6:30 AM
SCHEDULE_START_TIME=06:30
SCHEDULE_FREQUENCY_HOURS=6

# Check every hour, starting now + 5 minutes
SCHEDULE_FREQUENCY_HOURS=1

# Check every 12 hours, starting at 8:00 PM
SCHEDULE_START_TIME=20:00
SCHEDULE_FREQUENCY_HOURS=12
```

### Security Features

- **Credential Isolation**: All secrets stored in `.env` file
- **Prompt Injection Defense**: System prompt anchoring for LLM
- **Resource Bounds**: Transcript truncation at 12,000 characters
- **Input Validation**: Sanitization of external data
- **Web Setup Authentication**: Auth token required for all API requests
- **Web Setup CSRF Protection**: POST requests require CSRF token
- **Localhost Binding**: Web setup server bound to 127.0.0.1 only

## Testing

```bash
# Run all tests
python test_agent.py

# Run specific test class
python -m unittest test_agent.TestStateManager

# Run web setup tests
python -m pytest test_web_setup.py test_web_setup_api.py -v

# Run with coverage
pip install pytest-cov
pytest --cov=src test_agent.py
```

## Development

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for all public functions

### Adding New Skills

1. Create directory: `skills/your-skill-name/`
2. Add `SKILL.md` with YAML frontmatter
3. Include helper scripts in `scripts/` or `examples/`
4. Document usage and integration examples

## Troubleshooting

### Common Issues

1. **Ollama not connecting**
   - Ensure Ollama is running: `ollama serve`
   - Check if model is pulled: `ollama list`

2. **Telegram bot not responding**
   - Verify token in `.env`
   - Send at least one message to bot first
   - Check chat ID is correct

3. **YouTube video fetch failures (404/500 errors)**
   - YouTube's RSS feed may be blocked in some regions. Add a `YOUTUBE_API_KEY` for reliable access.
   - The program falls back automatically: API → RSS → HTML scraping. Check logs for which method succeeded.
   - Verify channel ID is correct (starts with `UC`, 24 characters).
    - If using an API key, check quota at Google Cloud Console (10,000/day free tier).
   - Test with a known working channel.

### Debug Mode

Set `LOG_LEVEL=DEBUG` in `.env` for verbose logging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Ollama](https://ollama.com/) for local LLM hosting
- [Telegram Bot API](https://core.telegram.org/bots/api) for messaging
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) for transcript extraction
- [feedparser](https://feedparser.readthedocs.io/) for RSS parsing

## Support

For issues and questions:
- Check [PREREQUISITES.md](PREREQUISITES.md) for setup help
- Review [Troubleshooting](#troubleshooting) section
- Open an issue on GitHub