# Browser-Based Setup Process

## Overview

The browser-based setup provides a visual web interface for configuring the YouTube Summarizer. It is the recommended setup method and is launched via:

```
python src/setup.py --web
```

The server runs locally on `http://127.0.0.1:8080` and automatically opens the browser.

---

## How It Works

### Launch (`src/setup.py:601-622`)

The entry point is in `setup.py`. When `--web` is passed, it imports and starts the `WebSetupServer` from `web_setup.py`:

```python
if "--web" in sys.argv:
    from web_setup import WebSetupServer
    server = WebSetupServer(port=8080)
    server.serve()
```

### Web Server (`src/web_setup.py`)

The server (`WebSetupServer` class) is built entirely on Python's standard library `http.server` — **no external web framework** (Flask, Django, etc.) is required.

**Key characteristics:**

- **Self-contained**: The entire HTML page (with inline CSS and JavaScript) is stored as a raw string in the `HTML_PAGE` variable.
- **No external templates**: Everything is embedded — no `.html` files, no frontend build tooling.
- **Localhost only**: The HTTPServer binds to `127.0.0.1`, making it inaccessible from the network.

### Security

| Measure | Implementation |
|---------|---------------|
| **Localhost binding** | Server binds to `127.0.0.1` only (line 718) |
| **Auth token** | Cryptographically random token (32 bytes, URL-safe base64) generated at startup, printed to terminal, required as `X-Auth-Token` header on all API requests |
| **CSRF token** | Separate random token embedded in the page JavaScript (`__CSRF_TOKEN__`), required as `X-CSRF-Token` header on all POST requests |
| **Token masking** | The Telegram bot token is masked in API responses — only the last 4 characters are shown (e.g., `****YZ12`) |
| **Audit logging** | All requests (method, path, status, client IP) are logged to `web_setup.log` |

### Startup Flow

1. `WebSetupServer.__init__` generates the auth token and CSRF token via `secrets.token_urlsafe(32)`
2. The server prints the auth token to the terminal
3. `WebSetupServer.serve()` prints the URL and opens the browser automatically via `webbrowser.open()`
4. The HTML page is served and the JavaScript reads `__AUTH_TOKEN__` and `__CSRF_TOKEN__` from placeholders replaced at serve time

---

## API Endpoints

All endpoints served by the same `HTTPServer`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serves the HTML setup page |
| `/api/config` | GET | Returns current configuration (with masked token) |
| `/api/channels/add` | POST | Add a YouTube channel by URL or channel ID |
| `/api/channels/delete` | POST | Remove a channel from the list |
| `/api/frequency` | POST | Set check frequency (1–24 hours) |
| `/api/telegram` | POST | Save Telegram bot credentials |
| `/api/save` | POST | Save entire configuration to `.env` at once |

**Authentication rules:**
- All requests (including GET) require `X-Auth-Token` header
- All POST requests additionally require `X-CSRF-Token` header

---

## Web UI Features

The HTML page (`src/web_setup.py:28-410`) contains three main sections:

### 1. YouTube Channels Section
- Text input for channel URLs (`https://www.youtube.com/@ChannelName`, `/c/name`, `/channel/UC...`)
- "Add" button that calls `POST /api/channels/add`
- The server-side `SetupWizard.extract_channel_id_from_url()` scrapes the YouTube page to resolve handles and custom URLs into channel IDs
- Validates channel ID format (must start with `UC`, 24 characters)
- Table showing all configured channels with "Delete" buttons
- Channel counter ("X of 100 channels configured")
- Supports pressing Enter in the input field

### 2. Check Frequency Section
- Number input (1–24) for how often to check for new videos
- "Enter" button to save via `POST /api/frequency`

### 3. Telegram Bot Configuration Section
- "Create / Configure Telegram Bot" button opens a **modal dialog** with:
  - Step-by-step instructions (use BotFather, get token, find chat ID via `getUpdates`)
  - Tutorial video: [How to create a Telegram bot, get Chat ID and Token](https://www.youtube.com/watch?v=l5YDtSLGhqk)
  - Fields: Chat ID, Bot Username, API Key (password-masked input)
  - Validation on the server: token format regex check, chat ID must be numeric
- After saving, shows a read-only summary with the masked API key

### 4. Save Button
- Saves all current state (channels, frequency, Telegram credentials) to `.env` file via `POST /api/save`
- Uses `python-dotenv`'s `set_key()` to write individual variables preserving existing values

---

## File Interaction

The setup process writes to `.env` in the project root directory. The following environment variables are managed:

| Variable | Example | Source |
|----------|---------|--------|
| `YOUTUBE_CHANNEL_IDS` | `UCabc123...,UCdef456...` | Channels section |
| `SCHEDULE_FREQUENCY_HOURS` | `6` | Frequency section |
| `TELEGRAM_BOT_TOKEN` | `123456:ABCdef...` | Telegram modal |
| `TELEGRAM_CHAT_ID` | `6758055228` | Telegram modal |
| `TELEGRAM_BOT_USERNAME` | `my_youtube_bot` | Telegram modal (optional) |

---

## Channel ID Extraction Logic

The `SetupWizard.extract_channel_id_from_url()` method (`src/setup.py:109-165`) supports these URL formats:

1. **Direct channel ID**: `youtube.com/channel/UCxxxxxx` — extracted via regex
2. **Custom URL / Handle** (e.g., `youtube.com/@handle`, `youtube.com/c/name`) — the page is fetched with a browser User-Agent header, then scanned for these patterns:
   - `"channelId":"UC..."` (YouTube embed data)
   - `"externalId":"UC..."` 
   - `channel_id=UC...`
   - RSS feed link containing the channel ID

If extraction fails, the API returns a 400 error with a descriptive message.

---

## Testing

Two test files validate the web setup server:

| File | Purpose |
|------|---------|
| `test_web_setup.py` | Tests for configuration loading, saving, and `.env` file handling |
| `test_web_setup_api.py` | Integration tests for all API endpoints (auth, channels, frequency, telegram, save) |

Tests use the `unittest` framework and rely on temporary files to avoid modifying the real `.env`.

---

## Source Files

| File | Role |
|------|------|
| `src/web_setup.py` | Web server, HTML page, API handlers (753 lines) |
| `src/setup.py` | Entry point (`--web` flag), channel ID extraction, validation logic (626 lines) |
| `test_web_setup.py` | Unit tests for config load/save |
| `test_web_setup_api.py` | Integration tests for all API endpoints |
