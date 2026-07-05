# YouTube Summarizer

A locally hosted, privacy-focused YouTube subscription summarizer that monitors your YouTube subscriptions via RSS feeds, extracts transcripts, generates AI-powered summaries using Ollama/Qwen, and delivers them to your Telegram.

## Features

- **Privacy-First**: All processing happens locally - no data sent to external AI services
- **RSS Feed Monitoring**: No YouTube API quota required
- **Local AI Summarization**: Uses Ollama with Qwen 2.5 models
- **Telegram Notifications**: Delivers formatted summaries directly to your chat
- **State Management**: SQLite database tracks processed videos
- **Smart Scheduling**: Configurable start time and frequency (1-24 hours)
- **Multi-Channel Support**: Monitor up to 100 YouTube channels
- **Modular Architecture**: Agent Skills pattern for reusability

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    YouTube Summarizer Pipeline                    │
├─────────────────────────────────────────────────────────────────┤
│  YouTube RSS Feeds  →  Transcript Extraction  →  Ollama/Qwen   │
│         ↓                      ↓                      ↓         │
│  State Manager  →  Agent Orchestrator  →  Telegram Notifier    │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Prerequisites
- Python 3.8+
- Ollama with qwen2.5:1.5b model
- Telegram bot token and chat ID
- YouTube channel IDs

See [PREREQUISITES.md](PREREQUISITES.md) for detailed setup instructions.

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/youtube-summarizer.git
cd youtube-summarizer

# Install dependencies
pip install -r requirements.txt

# Run setup wizard
python src/setup.py           # Terminal wizard
python src/setup.py --web     # Browser-based setup (recommended)
                              # The browser will be launched by the python code but it will take a while to initialize so be patient.
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
youtube-summarizer/
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
- Parse YouTube channel RSS feeds
- Extract video metadata
- No API quotas required

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
| `SCHEDULE_START_TIME` | No | Start time in HH:MM format (24-hour). Defaults to now + 5 min |
| `SCHEDULE_FREQUENCY_HOURS` | No | Check frequency in hours (1-24, default: 6) |
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

3. **YouTube RSS feed errors**
   - Verify channel ID is correct
   - Test with known working channel
   - Check network connectivity

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