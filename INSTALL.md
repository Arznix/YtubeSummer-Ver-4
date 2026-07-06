# Complete Installation Guide

This guide will walk you through setting up the YouTube Summarizer from scratch. Follow each section in order.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Install Python](#install-python)
3. [Install Ollama (AI Engine)](#install-ollama)
4. [Download AI Model](#download-ai-model)
5. [Install Project Files](#install-project-files)
6. [Install Python Dependencies](#install-python-dependencies)
7. [Create Telegram Bot](#create-telegram-bot)
8. [Configure the Application](#configure-the-application)
9. [Add YouTube Channels](#add-youtube-channels)
10. [Set Update Frequency](#set-update-frequency)
11. [Test the Installation](#test-the-installation)
12. [Run the Scheduler](#run-the-scheduler)
13. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **RAM**: 8 GB minimum (16 GB recommended)
- **Storage**: 10 GB free space
- **Internet**: Required for YouTube API and Telegram

### Recommended Requirements
- **RAM**: 16 GB or more
- **CPU**: Modern multi-core processor
- **GPU**: Optional but faster with NVIDIA GPU (4GB+ VRAM)

---

## Install Python

### Windows

1. **Download Python**
   - Go to https://www.python.org/downloads/
   - Click "Download Python 3.12" (or latest version)

2. **Run Installer**
   - Double-click the downloaded file
   - **IMPORTANT**: Check "Add Python to PATH" checkbox
   - Click "Install Now"
   - Wait for installation to complete

3. **Verify Installation**
   - Open Command Prompt (Win+R, type `cmd`, press Enter)
   - Type: `python --version`
   - You should see: `Python 3.12.x`

### macOS

1. **Download Python**
   - Go to https://www.python.org/downloads/
   - Download the macOS installer

2. **Run Installer**
   - Double-click the .pkg file
   - Follow the prompts
   - Click "Install"

3. **Verify Installation**
   - Open Terminal
   - Type: `python3 --version`

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
python3 --version
```

---

## Install Ollama

Ollama is the local AI engine that runs the summarization model.

### Windows

1. **Download Ollama**
   - Go to https://ollama.com/download
   - Click "Download for Windows"

2. **Run Installer**
   - Double-click the downloaded file
   - Follow the installation prompts
   - Restart your computer when prompted

3. **Verify Installation**
   - Open Command Prompt
   - Type: `ollama --version`
   - You should see version information

### macOS

1. **Download Ollama**
   - Go to https://ollama.com/download
   - Click "Download for macOS"

2. **Install**
   - Drag Ollama to your Applications folder
   - Open Ollama from Applications
   - Follow the setup prompts

3. **Verify Installation**
   - Open Terminal
   - Type: `ollama --version`

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama --version
```

---

## Download AI Model

After installing Ollama, download the Qwen 2.5 model:

### Step 1: Start Ollama

- **Windows**: Ollama starts automatically. Check system tray for the Ollama icon.
- **macOS**: Open Ollama from Applications
- **Linux**: Run `ollama serve` in terminal

### Step 2: Download the Model

Open Command Prompt/Terminal and run:

```bash
ollama pull qwen2.5:1.5b
```

This will download approximately 1 GB. Wait for completion.

### Step 3: Verify Model

```bash
ollama list
```

You should see `qwen2.5:1.5b` in the list.

---

## Install Project Files

### Option 1: Download from GitHub (Recommended)

1. **Install Git** (if not installed)
   - Windows: https://git-scm.com/download/win
   - macOS: `xcode-select --install`
   - Linux: `sudo apt install git`

2. **Clone Repository**
   ```bash
   git clone https://github.com/Arznix/youtube-summarizer.git
   cd youtube-summarizer
   ```

### Option 2: Download ZIP

1. Go to https://github.com/Arznix/youtube-summarizer
2. Click "Code" → "Download ZIP"
3. Extract the ZIP file
4. Open terminal in the extracted folder

---

## Install Python Dependencies

### Step 1: Create Virtual Environment

```bash
python -m venv venv
```

### Step 2: Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
pip list
```

You should see packages like:
- requests
- python-dotenv
- feedparser
- youtube-transcript-api

---

## Create Telegram Bot

### Step 1: Create Bot with BotFather

1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Enter a name for your bot (e.g., "YouTube Summarizer")
5. Enter a username (e.g., "youtube_summary_bot")
6. BotFather will give you a **bot token**
   - Copy this token (looks like: `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`)

### Step 2: Get Your Chat ID

1. Open Telegram
2. Search for your new bot by username
3. Send `/start` to your bot
4. Open this URL in your browser (replace `YOUR_TOKEN` with your bot token):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
5. Look for `"chat":{"id":` in the response
6. Copy the chat ID number (e.g., `6758055228`)

---

## Configure the Application

### Step 1: Create Configuration File

```bash
copy .env.example .env
```

### Step 2: Edit Configuration File

Open `.env` in a text editor (Notepad, VS Code, etc.):

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b

# YouTube Channel IDs (will add in next step)
YOUTUBE_CHANNEL_IDS=

# Scheduling Configuration
SCHEDULE_FREQUENCY_HOURS=6
```

Replace:
- `YOUR_BOT_TOKEN_HERE` with your Telegram bot token
- `YOUR_CHAT_ID_HERE` with your Telegram chat ID

### Option 3: Web Browser Setup (Recommended)

The web setup provides a visual interface for configuring your system:

```bash
# Start web setup server
python src/setup.py --web

# Or specify a custom port
python src/setup.py --web --port 8080
```

The server will:
1. Print an authentication token to the terminal
2. Open your browser to `http://127.0.0.1:8080`
3. Display the setup page (auth token is embedded automatically)

**Security features:**
- Server bound to localhost only (not network accessible)
- Auth token required for all API requests
- CSRF protection for all POST requests
- Bot token masked in browser UI
- All requests logged to `web_setup.log`

---

## Add YouTube Channels

### Method 1: Using Channel URLs (Recommended)

Use the included script to extract channel IDs from URLs:

```bash
python extract_channel_id.py https://www.youtube.com/@veritasium
```

Output:
```
[OK] Channel ID: UCin0m13qWv3-051xlWlHamA
```

### Method 2: Manual Channel ID Extraction

1. Go to the YouTube channel page
2. View page source (Ctrl+U on Windows, Cmd+Option+U on macOS)
3. Search for `channelId` or `externalId`
4. Copy the channel ID (starts with `UC`)

### Method 3: Use Setup Wizard

```bash
python src/setup.py
```

Follow the prompts to add channels.

### Method 4: Web UI

Use the browser-based setup for a visual channel management interface:

```bash
python src/setup.py --web
```

The web UI allows you to:
- Add channels by URL, ID, or handle
- Remove channels with one click
- View RSS URLs and validation status
- Save configuration with a single button

### Example: Adding Multiple Channels

Edit your `.env` file and add channel IDs separated by commas:

```env
YOUTUBE_CHANNEL_IDS=UCHnyfMqiRRG1u-2MsSQLbXA,UCG7J20LhUeLl6y_Emi7OJrA,UC1_uAIS3r8Vu6JjXWvastJg
```

### Popular Channels to Follow

| Channel | Channel ID |
|---------|------------|
| Veritasium | UCHnyfMqiRRG1u-2MsSQLbXA |
| MKBHD | UCG7J20LhUeLl6y_Emi7OJrA |
| 3Blue1Brown | UC1_uAIS3r8Vu6JjXWvastJg |
| Kurzgesagt | UCq8ZAAsI89IoJ-fn1gYpO3g |
| SmarterEveryDay | UC8VkNBOwvsTlFjoSnNSMmxw |
| Vsauce | UC6nSFpj9HTCZ5t-N3Rm3-HA |
| Mark Rober | UC513PdAP2-jWkJunTh5kXRw |
| Computerphile | UCoxcjq-8xIDTYp3uz647V5A |
| Numberphile | UCtwKon9qMt5YLVgQt1tvJKg |
| TED | UCsT0YIqwnpJCM-mx7-gSA4Q |

**Maximum channels**: 100

---

## Set Update Frequency

### Option 1: Using Setup Wizard

```bash
python src/setup.py
```

Follow the scheduling prompts.

### Option 2: Edit Configuration File

Open `.env` and set:

```env
# Check every 6 hours (default)
SCHEDULE_FREQUENCY_HOURS=6

# Or check every hour
SCHEDULE_FREQUENCY_HOURS=1

# Or check every 12 hours
SCHEDULE_FREQUENCY_HOURS=12
```

### Scheduling Options

| Setting | Description |
|---------|-------------|
| Start Time | Optional. Set to start at specific time (e.g., `06:30`) |
| Frequency | How often to check (1-24 hours) |
| Default | If no start time, starts 5 minutes after launch |

### Example Configurations

```env
# Check every 6 hours, starting at 6:30 AM
SCHEDULE_START_TIME=06:30
SCHEDULE_FREQUENCY_HOURS=6

# Check every hour, starting now
SCHEDULE_FREQUENCY_HOURS=1

# Check every 12 hours, starting at 8:00 PM
SCHEDULE_START_TIME=20:00
SCHEDULE_FREQUENCY_HOURS=12
```

---

## Test the Installation

### Step 1: Check Configuration

```bash
python src/agent_orchestrator.py --status
```

Expected output:
```
Orchestrator Status:
  running: False
  channels_configured: 10
  schedule_frequency_hours: 6
  ...
```

### Step 2: Run Once

```bash
python src/agent_orchestrator.py --once
```

This will:
1. Check all configured channels for new videos
2. Extract transcripts
3. Generate AI summaries
4. Send summaries to Telegram

### Step 3: Check Telegram

Open your Telegram bot chat. You should receive video summaries.

---

## Run the Scheduler

### Option 1: Foreground (Simple)

```bash
python src/agent_orchestrator.py
```

This keeps running until you press Ctrl+C.

### Option 2: Background (Windows)

```bash
pythonw src/agent_orchestrator.py
```

### Option 3: Background (Linux/macOS)

```bash
nohup python src/agent_orchestrator.py > logs/scheduler.log 2>&1 &
```

### Option 4: Using Task Scheduler (Windows)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., at startup)
4. Set action: Start `python` with arguments `src/agent_orchestrator.py`
5. Set start folder to project directory

### Check Status

```bash
python src/agent_orchestrator.py --status
```

---

## Troubleshooting

### Problem: Python not found

**Solution**: Add Python to PATH
- Windows: Reinstall Python with "Add to PATH" checked
- Or manually add Python folder to PATH

### Problem: Ollama not connecting

**Solution**:
1. Ensure Ollama is running (check system tray)
2. Test connection: `curl http://localhost:11434/api/tags`
3. If using different port, update `OLLAMA_HOST` in `.env`

### Problem: Model not found

**Solution**:
```bash
ollama pull qwen2.5:1.5b
ollama list
```

### Problem: Telegram bot not responding

**Solution**:
1. Verify bot token is correct
2. Send `/start` to your bot
3. Verify chat ID is correct
4. Test with: `curl https://api.telegram.org/botYOUR_TOKEN/getMe`

### Problem: No transcripts found

**Solution**:
- Some videos don't have transcripts
- Check if video has captions enabled
- The system will skip videos without transcripts

### Problem: Slow processing

**Solution**:
- The 1.5B model is fast; 7B model is slower
- Reduce number of channels
- Increase check frequency to process fewer videos at once

### Problem: Module not found error

**Solution**:
```bash
# Ensure virtual environment is activated
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Reinstall dependencies
pip install -r requirements.txt
```

---

## Quick Reference

### Common Commands

```bash
# Check status
python src/agent_orchestrator.py --status

# Run once
python src/agent_orchestrator.py --once

# Run scheduler
python src/agent_orchestrator.py

# Add channel
python extract_channel_id.py https://www.youtube.com/@channelname

# Setup wizard (terminal)
python src/setup.py

# Web setup (browser-based, recommended)
python src/setup.py --web

# Run tests
python test_agent.py

# Run web setup tests
python -m pytest test_web_setup.py test_web_setup_api.py -v
```

### Configuration File Locations

| File | Purpose |
|------|---------|
| `.env` | Main configuration (secrets, channels, schedule) |
| `.env.example` | Configuration template |
| `data/subscriptions_state.db` | Video processing state |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Yes | Your Telegram chat ID |
| `OLLAMA_HOST` | Yes | Ollama server URL |
| `OLLAMA_MODEL` | No | AI model name (default: qwen2.5:1.5b) |
| `YOUTUBE_CHANNEL_IDS` | Yes | Comma-separated channel IDs |
| `SCHEDULE_START_TIME` | No | Start time (HH:MM format) |
| `SCHEDULE_FREQUENCY_HOURS` | No | Check frequency (1-24 hours) |

---

## Support

If you encounter issues:

1. Check this troubleshooting guide
2. Run tests: `python test_agent.py`
3. Check logs in terminal output
4. Visit: https://github.com/Arznix/youtube-summarizer

---

## Summary

You have successfully installed:
- Python 3.x
- Ollama with Qwen 2.5 1.5B model
- YouTube Summarizer application
- Telegram bot integration

Your system will now:
- Monitor YouTube channels for new videos
- Extract video transcripts
- Generate AI-powered summaries
- Send summaries to your Telegram

**Next step**: Run `python src/agent_orchestrator.py` to start monitoring!
