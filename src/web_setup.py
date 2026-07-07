import os
import sys
import json
import time
import secrets
import logging
import webbrowser
import threading
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv, set_key

from setup import SetupWizard
from config import KEYRING_SERVICE, get_config_dir, _keyring_get, _keyring_set, _read_credential_file, _write_credential_file


# Setup request audit logger
_audit_logger = logging.getLogger("web_setup.audit")
_audit_logger.setLevel(logging.INFO)
_handler = logging.FileHandler("web_setup.log")
_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
_audit_logger.addHandler(_handler)
_audit_logger.propagate = False


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ytube Summarizer - Setup</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
h1 { color: red; font-family: Arial, sans-serif; font-size: 60pt; text-align: center; margin-bottom: 10px; }
.description { font-size: 14px; color: #333; line-height: 1.6; margin-bottom: 30px; padding: 15px; background: #fff; border-radius: 8px; border: 1px solid #ddd; }
.section { background: #fff; padding: 20px; margin-bottom: 20px; border-radius: 8px; border: 1px solid #ddd; }
.section h2 { font-size: 18px; color: #333; margin-bottom: 15px; border-bottom: 2px solid #007bff; padding-bottom: 8px; }
label { display: block; font-weight: bold; margin-bottom: 6px; color: #444; }
.input-row { display: flex; gap: 10px; align-items: center; margin-bottom: 15px; }
.input-row input[type="text"], .input-row input[type="number"] { flex: 1; padding: 8px 12px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
.input-row input[type="number"] { max-width: 100px; }
button { padding: 8px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: bold; }
.btn-add { background: #28a745; color: white; }
.btn-add:hover { background: #218838; }
.btn-delete { background: #dc3545; color: white; padding: 4px 12px; font-size: 12px; }
.btn-delete:hover { background: #c82333; }
.btn-enter { background: #007bff; color: white; }
.btn-enter:hover { background: #0069d9; }
.btn-save { background: #17a2b8; color: white; font-size: 16px; padding: 12px 30px; display: block; margin: 20px auto; }
.btn-save:hover { background: #138496; }
.btn-telegram { background: #0088cc; color: white; font-size: 14px; padding: 10px 20px; }
.btn-telegram:hover { background: #006da3; }
.table-container { max-height: 400px; overflow-y: auto; border: 1px solid #ccc; border-radius: 4px; margin-top: 10px; }
table { width: 100%; border-collapse: collapse; }
th { background: #007bff; color: white; padding: 10px; text-align: left; position: sticky; top: 0; }
td { padding: 8px 10px; border-bottom: 1px solid #eee; }
tr:hover { background: #f0f0f0; }
.channel-count { margin-top: 10px; color: #666; font-size: 13px; }
.status-msg { padding: 8px 12px; border-radius: 4px; margin-top: 10px; font-size: 13px; display: none; }
.status-ok { display: block; background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
.status-err { display: block; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
.telegram-fields { margin-top: 15px; padding: 10px; background: #e9ecef; border-radius: 4px; }
.telegram-fields p { margin: 5px 0; font-size: 13px; }
.modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; justify-content: center; align-items: center; }
.modal-overlay.active { display: flex; }
.modal-content { background: white; padding: 30px; border-radius: 8px; max-width: 550px; width: 90%; max-height: 80vh; overflow-y: auto; }
.modal-content h3 { margin-bottom: 15px; color: #333; }
.modal-content p { margin: 8px 0; font-size: 13px; line-height: 1.5; color: #555; }
.modal-content label { margin-top: 12px; }
.modal-content input[type="text"], .modal-content input[type="password"] { width: 100%; padding: 8px 12px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; margin-top: 4px; }
.modal-buttons { display: flex; gap: 10px; margin-top: 20px; }
.modal-buttons button { flex: 1; padding: 10px; }
.btn-cancel { background: #6c757d; color: white; }
.btn-cancel:hover { background: #5a6268; }
.btn-modal-enter { background: #28a745; color: white; }
.btn-modal-enter:hover { background: #218838; }
.warning { background: #fff3cd; color: #856404; padding: 10px; border-radius: 4px; border: 1px solid #ffc107; margin-top: 15px; font-size: 13px; }
.auth-banner { background: #cce5ff; color: #004085; padding: 10px 15px; border-radius: 4px; border: 1px solid #b8daff; margin-bottom: 20px; font-size: 13px; text-align: center; }
</style>
</head>
<body>

<h1>Ytube Summarizer</h1>

<div class="auth-banner" id="auth-banner"></div>

<div class="description">
Ytube Summarize sends text summaries of new videos from your favorite YouTube creators.
Stop wasting time watching videos that are not relevant to you now.
Receive summaries of the videos on your Telegram feed.
Only watch the videos that seem interesting to you.
</div>

<!-- YouTube Channels Section -->
<div class="section">
<h2>YouTube Channels</h2>
<label for="channel-url">Enter the URL of the homepage of each of the YouTube creators you want to follow:</label>
<div class="input-row">
<input type="text" id="channel-url" placeholder="https://www.youtube.com/@ChannelName">
<button class="btn-add" onclick="addChannel()">Add</button>
</div>
<div id="channel-status" class="status-msg"></div>
<div class="table-container">
<table>
<thead><tr><th>#</th><th>Channel ID</th><th>Action</th></tr></thead>
<tbody id="channel-tbody"></tbody>
</table>
</div>
<p class="channel-count" id="channel-count"></p>
</div>

<!-- Frequency Section -->
<div class="section">
<h2>Check Frequency</h2>
<label for="freq-input">Enter how often you want to check each of the channels in your list. Enter a number between 1 and 24:</label>
<div class="input-row">
<input type="number" id="freq-input" min="1" max="24" value="6">
<button class="btn-enter" onclick="saveFrequency()">Enter</button>
<span id="freq-status" style="margin-left:10px; font-size:13px;"></span>
</div>
</div>

<!-- Ollama Section -->
<div class="section">
<h2>Ollama Configuration</h2>
<label for="ollama-host">Ollama Host URL:</label>
<div class="input-row">
<input type="text" id="ollama-host" value="http://localhost:11434">
<button class="btn-enter" onclick="saveOllama()">Enter</button>
<span id="ollama-status" style="margin-left:10px; font-size:13px;"></span>
</div>
<label for="ollama-model">Model Name:</label>
<div class="input-row">
<input type="text" id="ollama-model" placeholder="qwen2.5:1.5b">
<button class="btn-enter" onclick="saveOllama()">Enter</button>
</div>
</div>

<!-- Telegram Section -->
<div class="section">
<h2>Telegram Bot Configuration</h2>
<p>You need to create a Telegram Bot to receive your summaries. Activate the button below to get an explanation of the process.</p>
<button class="btn-telegram" onclick="openTelegramDialog()" style="margin-top:10px;">Create / Configure Telegram Bot</button>
<div class="telegram-fields" id="telegram-fields" style="display:none;">
<p><strong>Chatbot ID:</strong> <span id="tg-chat-id-display">-</span></p>
<p><strong>Chatbot Username:</strong> <span id="tg-username-display">-</span></p>
<p><strong>API Key:</strong> <span id="tg-token-display">-</span></p>
</div>
</div>

<!-- YouTube API Key Section -->
<div class="section">
<h2>YouTube Data API Key (optional)</h2>
<p>Using an API key is more reliable than RSS scraping. Get one free at
<a href="https://console.cloud.google.com/apis/library/youtube.googleapis.com" target="_blank">Google Cloud Console</a>.
If left blank, the program will fall back to scraping.</p>
<label for="youtube-api-key">API Key:</label>
<div class="input-row">
<input type="text" id="youtube-api-key" placeholder="AIzaSy...">
<button class="btn-enter" onclick="saveApiKey()">Enter</button>
<span id="apikey-status" style="margin-left:10px; font-size:13px;"></span>
</div>
</div>

<!-- Save Button -->
<button class="btn-save" onclick="saveAll()">Save Configuration</button>
<div id="save-status" class="status-msg" style="text-align:center;"></div>

<!-- Telegram Modal -->
<div class="modal-overlay" id="telegram-modal">
<div class="modal-content">
<h3>Telegram Bot Setup</h3>
<p>To create a Telegram bot:</p>
<ol style="margin:8px 0 8px 20px; font-size:13px; color:#555;">
<li>Open Telegram and search for <strong>@BotFather</strong></li>
<li>Send <strong>/newbot</strong> and follow the instructions</li>
<li>Copy the bot token (format: <code>123456789:ABCdefGHIjklMNOpqrSTUvwxYZ</code>)</li>
<li>To find your chat ID, send a message to your bot, then visit:<br>
<code>https://api.telegram.org/bot&lt;YOUR_TOKEN&gt;/getUpdates</code></li>
<li>Your chat ID will be a number like: <code>123456789</code></li>
</ol>

<label for="modal-chat-id">Chatbot ID:</label>
<input type="text" id="modal-chat-id" placeholder="e.g. 6758055228">

<label for="modal-username">Chatbot Username:</label>
<input type="text" id="modal-username" placeholder="e.g. my_youtube_bot">

<label for="modal-token">API Key (Bot Token):</label>
<input type="password" id="modal-token" placeholder="e.g. 123456789:ABCdefGHIjklMNOpqrSTUvwxYZ">

<p style="margin-top:15px; font-weight:bold; color:#856404;">You need to enter your chatbot ID and API key before you hit the ENTER button.</p>

<div class="warning">
Remember to save your Chat ID and API Key in a safe place. You will need them if you ever need to recreate or reconfigure the bot.
</div>

<div class="modal-buttons">
<button class="btn-modal-enter" onclick="saveTelegram()">ENTER</button>
<button class="btn-cancel" onclick="closeTelegramDialog()">CANCEL</button>
</div>
</div>
</div>

<script>
var CSRF_TOKEN = "__CSRF_TOKEN__";
var AUTH_TOKEN = "__AUTH_TOKEN__";

function apiHeaders() {
    return {
        'Content-Type': 'application/json',
        'X-CSRF-Token': CSRF_TOKEN,
        'X-Auth-Token': AUTH_TOKEN
    };
}

var state = {
    channels: [],
    frequency: 6,
    ollama_host: 'http://localhost:11434',
    ollama_model: 'qwen2.5:1.5b',
    telegram: { token: '', chat_id: '', username: '' },
    youtube_api_key: ''
};

var telegram_entered = false;

function init() {
    fetch('/api/config', { headers: { 'X-Auth-Token': AUTH_TOKEN } })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        state.channels = data.youtube_channel_ids || [];
        state.frequency = data.schedule_frequency_hours || 6;
        state.ollama_host = data.ollama_host || 'http://localhost:11434';
        state.ollama_model = data.ollama_model || 'qwen2.5:1.5b';
        document.getElementById('ollama-host').value = state.ollama_host;
        document.getElementById('ollama-model').value = state.ollama_model;
        state.youtube_api_key = data.youtube_api_key || '';
        document.getElementById('youtube-api-key').value = state.youtube_api_key;
        state.telegram = {
            token: data.telegram_bot_token || '',
            chat_id: data.telegram_chat_id || '',
            username: data.telegram_bot_username || ''
        };
        telegram_entered = false;
        document.getElementById('freq-input').value = state.frequency;
        document.getElementById('auth-banner').textContent =
            'Session active. Server bound to 127.0.0.1 only.';
        renderChannels();
        renderTelegramFields();
    })
    .catch(function() {
        document.getElementById('auth-banner').textContent =
            'Authentication failed. Reload the page from the terminal command.';
    });
}

function renderChannels() {
    var tbody = document.getElementById('channel-tbody');
    tbody.innerHTML = '';
    for (var i = 0; i < state.channels.length; i++) {
        var tr = document.createElement('tr');
        var tdNum = document.createElement('td');
        tdNum.textContent = (i + 1);
        var tdId = document.createElement('td');
        tdId.textContent = state.channels[i];
        var tdAction = document.createElement('td');
        var btn = document.createElement('button');
        btn.className = 'btn-delete';
        btn.textContent = 'Delete';
        btn.setAttribute('data-id', state.channels[i]);
        btn.onclick = (function(id) {
            return function() { deleteChannel(id); };
        })(state.channels[i]);
        tdAction.appendChild(btn);
        tr.appendChild(tdNum);
        tr.appendChild(tdId);
        tr.appendChild(tdAction);
        tbody.appendChild(tr);
    }
    document.getElementById('channel-count').textContent =
        state.channels.length + ' of 100 channels configured';
}

function renderTelegramFields() {
    var fieldsDiv = document.getElementById('telegram-fields');
    if (state.telegram.chat_id || state.telegram.token) {
        fieldsDiv.style.display = 'block';
        document.getElementById('tg-chat-id-display').textContent =
            state.telegram.chat_id || '-';
        document.getElementById('tg-username-display').textContent =
            state.telegram.username || '-';
        document.getElementById('tg-token-display').textContent =
            state.telegram.token ? '****' + state.telegram.token.slice(-4) : '-';
    }
}

function showStatus(elementId, msg, isError) {
    var el = document.getElementById(elementId);
    el.textContent = msg;
    el.className = 'status-msg ' + (isError ? 'status-err' : 'status-ok');
    setTimeout(function() { el.className = 'status-msg'; }, 4000);
}

function addChannel() {
    var urlInput = document.getElementById('channel-url');
    var url = urlInput.value.trim();
    if (!url) {
        showStatus('channel-status', 'Please enter a URL.', true);
        return;
    }
    fetch('/api/channels/add', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({url: url})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            showStatus('channel-status', data.error, true);
        } else {
            state.channels = data.channels;
            renderChannels();
            urlInput.value = '';
            showStatus('channel-status', 'Channel added: ' + data.channel_id, false);
        }
    })
    .catch(function(err) {
        showStatus('channel-status', 'Network error: ' + err.message, true);
    });
}

function deleteChannel(channelId) {
    fetch('/api/channels/delete', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({channel_id: channelId})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            showStatus('channel-status', data.error, true);
        } else {
            state.channels = data.channels;
            renderChannels();
            showStatus('channel-status', 'Channel removed.', false);
        }
    })
    .catch(function(err) {
        showStatus('channel-status', 'Network error: ' + err.message, true);
    });
}

function saveFrequency() {
    var val = parseInt(document.getElementById('freq-input').value, 10);
    if (isNaN(val) || val < 1 || val > 24) {
        document.getElementById('freq-status').textContent = 'Must be between 1 and 24.';
        document.getElementById('freq-status').style.color = 'red';
        return;
    }
    fetch('/api/frequency', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({frequency: val})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            document.getElementById('freq-status').textContent = data.error;
            document.getElementById('freq-status').style.color = 'red';
        } else {
            state.frequency = data.frequency;
            document.getElementById('freq-status').textContent = 'Saved: every ' + data.frequency + ' hour(s)';
            document.getElementById('freq-status').style.color = 'green';
        }
    });
}

function openTelegramDialog() {
    document.getElementById('telegram-modal').classList.add('active');
    document.getElementById('modal-chat-id').value = state.telegram.chat_id || '';
    document.getElementById('modal-username').value = state.telegram.username || '';
    document.getElementById('modal-token').value = '';
}

function closeTelegramDialog() {
    document.getElementById('telegram-modal').classList.remove('active');
}

function saveTelegram() {
    var chatId = document.getElementById('modal-chat-id').value.trim();
    var username = document.getElementById('modal-username').value.trim();
    var token = document.getElementById('modal-token').value.trim();

    if (!chatId || !token) {
        alert('You need to enter your chatbot ID and API key before you hit the ENTER button.');
        return;
    }

    fetch('/api/telegram', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({chat_id: chatId, username: username, bot_token: token})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            alert(data.error);
        } else {
            telegram_entered = true;
            state.telegram.chat_id = chatId;
            state.telegram.username = username;
            state.telegram.token = token;
            renderTelegramFields();
            closeTelegramDialog();
        }
    });
}

function saveOllama() {
    var host = document.getElementById('ollama-host').value.trim();
    var model = document.getElementById('ollama-model').value.trim();
    if (!host) {
        document.getElementById('ollama-status').textContent = 'Host is required.';
        document.getElementById('ollama-status').style.color = 'red';
        return;
    }
    if (!host.startsWith('http://') && !host.startsWith('https://')) {
        document.getElementById('ollama-status').textContent = 'Host must start with http:// or https://';
        document.getElementById('ollama-status').style.color = 'red';
        return;
    }
    fetch('/api/ollama', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({ollama_host: host, ollama_model: model || 'qwen2.5:1.5b'})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            document.getElementById('ollama-status').textContent = data.error;
            document.getElementById('ollama-status').style.color = 'red';
        } else {
            state.ollama_host = host;
            state.ollama_model = model || 'qwen2.5:1.5b';
            document.getElementById('ollama-status').textContent = 'Ollama settings saved.';
            document.getElementById('ollama-status').style.color = 'green';
        }
    });
}

function saveApiKey() {
    var key = document.getElementById('youtube-api-key').value.trim();
    fetch('/api/youtube-api-key', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({youtube_api_key: key})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            document.getElementById('apikey-status').textContent = data.error;
            document.getElementById('apikey-status').style.color = 'red';
        } else {
            state.youtube_api_key = key;
            document.getElementById('apikey-status').textContent = 'API key saved.';
            document.getElementById('apikey-status').style.color = 'green';
        }
    });
}

function saveAll() {
    var freqVal = parseInt(document.getElementById('freq-input').value, 10);
    if (isNaN(freqVal) || freqVal < 1 || freqVal > 24) {
        freqVal = state.frequency;
    }
    var body = {
        youtube_channel_ids: state.channels,
        schedule_frequency_hours: freqVal,
        ollama_host: document.getElementById('ollama-host').value.trim() || state.ollama_host,
        ollama_model: document.getElementById('ollama-model').value.trim() || state.ollama_model,
        youtube_api_key: document.getElementById('youtube-api-key').value.trim() || state.youtube_api_key,
    };
    if (telegram_entered) {
        body.telegram_chat_id = state.telegram.chat_id;
        body.telegram_bot_username = state.telegram.username;
        body.telegram_bot_token = state.telegram.token;
    }
    fetch('/api/save', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify(body)
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            showStatus('save-status', data.error, true);
        } else {
            state.frequency = freqVal;
            state.ollama_host = document.getElementById('ollama-host').value.trim() || state.ollama_host;
            state.ollama_model = document.getElementById('ollama-model').value.trim() || state.ollama_model;
            state.youtube_api_key = document.getElementById('youtube-api-key').value.trim() || state.youtube_api_key;
            showStatus('save-status', 'Configuration saved successfully!', false);
        }
    })
    .catch(function(err) {
        showStatus('save-status', 'Save failed: ' + err.message, true);
    });
}

document.getElementById('channel-url').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') addChannel();
});

init();
</script>

</body>
</html>"""


def _mask_token(token: str) -> str:
    """Mask a sensitive token, showing only last 4 characters."""
    if not token or len(token) <= 4:
        return "***"
    return "***" + token[-4:]


class WebSetupServer:
    """Browser-based setup server for YouTube Summarizer.

    Security notes:
    - Server binds to 127.0.0.1 only (localhost). Not accessible from network.
    - All API requests require X-Auth-Token header matching the startup token.
    - All POST requests require X-CSRF-Token header matching the page token.
    - Bot token is masked in GET /api/config responses.
    - All requests are logged to web_setup.log for audit.
    """

    def __init__(self, port=8080):
        self.port = port
        self.project_root = Path(__file__).parent.parent
        self.config_dir = get_config_dir()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.env_file = self.config_dir / ".env"
        self._wizard = SetupWizard()
        # Generate auth token (printed to terminal, required for all API calls)
        self._auth_token = secrets.token_urlsafe(32)
        # Generate CSRF token (embedded in HTML page, required for POST calls)
        self._csrf_token = secrets.token_urlsafe(32)

    def _load_env(self) -> dict:
        if self.env_file.exists():
            load_dotenv(self.env_file, override=True)

        token = _keyring_get(KEYRING_SERVICE, "telegram_bot_token")
        chat_id = _keyring_get(KEYRING_SERVICE, "telegram_chat_id")
        yt_key = _keyring_get(KEYRING_SERVICE, "youtube_api_key")

        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        if not ollama_host.startswith(("http://", "https://")):
            ollama_host = "http://localhost:11434"

        return {
            "TELEGRAM_BOT_TOKEN": token or os.getenv("TELEGRAM_BOT_TOKEN", ""),
            "TELEGRAM_CHAT_ID": chat_id or os.getenv("TELEGRAM_CHAT_ID", ""),
            "TELEGRAM_BOT_USERNAME": os.getenv("TELEGRAM_BOT_USERNAME", ""),
            "OLLAMA_HOST": ollama_host,
            "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
            "YOUTUBE_CHANNEL_IDS": os.getenv("YOUTUBE_CHANNEL_IDS", ""),
            "YOUTUBE_API_KEY": yt_key or os.getenv("YOUTUBE_API_KEY", ""),
            "SCHEDULE_FREQUENCY_HOURS": os.getenv("SCHEDULE_FREQUENCY_HOURS", "6"),
            "SCHEDULE_START_TIME": os.getenv("SCHEDULE_START_TIME", ""),
        }

    def _save_env(self, updates: dict):
        env_path = str(self.env_file)
        if not self.env_file.exists():
            self.env_file.touch()

        sensitive_keys = {"TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "YOUTUBE_API_KEY"}
        keyring_updates = {}
        env_updates = {}

        for key, value in updates.items():
            if key in sensitive_keys:
                keyring_updates[key] = value
            else:
                env_updates[key] = value

        # Strip sensitive keys from .env file to avoid duplication
        try:
            if self.env_file.exists():
                lines = self.env_file.read_text().splitlines(keepends=True)
                filtered = [l for l in lines if not any(
                    l.strip().startswith(k + "=") for k in sensitive_keys
                )]
                self.env_file.write_text("".join(filtered))
        except OSError as exc:
            _audit_logger.warning(f"Could not strip sensitive keys from .env: {exc}")

        # Remove sensitive keys from current process env
        for key in sensitive_keys:
            os.environ.pop(key, None)

        # Store sensitive credentials in OS keychain + fallback credential file
        try:
            has_tg = "TELEGRAM_BOT_TOKEN" in keyring_updates or "TELEGRAM_CHAT_ID" in keyring_updates
            has_yt = "YOUTUBE_API_KEY" in keyring_updates
            if has_tg or has_yt:
                creds = _read_credential_file(self.config_dir)
                token = keyring_updates.get("TELEGRAM_BOT_TOKEN")
                chat_id = keyring_updates.get("TELEGRAM_CHAT_ID")
                if token:
                    _keyring_set(KEYRING_SERVICE, "telegram_bot_token", str(token))
                    creds["telegram_bot_token"] = token
                if chat_id:
                    _keyring_set(KEYRING_SERVICE, "telegram_chat_id", str(chat_id))
                    creds["telegram_chat_id"] = chat_id
                if has_yt:
                    yt_key = keyring_updates.get("YOUTUBE_API_KEY", "")
                    if yt_key:
                        _keyring_set(KEYRING_SERVICE, "youtube_api_key", str(yt_key))
                        creds["youtube_api_key"] = yt_key
                    else:
                        _keyring_delete(KEYRING_SERVICE, "youtube_api_key")
                        creds.pop("youtube_api_key", None)
                _write_credential_file(self.config_dir, creds)
        except Exception as exc:
            _audit_logger.warning(f"Could not store sensitive credentials: {exc}")

        # Store non-sensitive config in .env
        try:
            if env_updates:
                lines = []
                if self.env_file.exists():
                    raw = self.env_file.read_text(encoding="utf-8")
                    lines = raw.splitlines()
                # Remove any existing lines whose key matches what we're updating
                update_keys = set(env_updates.keys())
                lines = [l for l in lines if not any(
                    l.strip().startswith(k + "=") for k in update_keys
                )]
                # Remove sensitive keys again just in case
                lines = [l for l in lines if not any(
                    l.strip().startswith(k + "=") for k in sensitive_keys
                )]
                # Append new values
                for key, value in env_updates.items():
                    lines.append(f"{key}={value}")
                content = "\n".join(lines) + "\n"
                self.env_file.write_text(content, encoding="utf-8")
                _audit_logger.info(f"Saved {len(env_updates)} settings to {self.env_file}")
        except Exception as exc:
            _audit_logger.error(f"Failed to save .env: {exc}")

    def _make_handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def _log_audit(self, method, path, status):
                client = self.client_address[0] if self.client_address else "?"
                _audit_logger.info("%s %s %d %s", method, path, status, client)

            def _send_json(self, data, status=200):
                body = json.dumps(data).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_html(self, html):
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _read_body(self) -> dict:
                length = int(self.headers.get("Content-Length", 0))
                if length == 0:
                    return {}
                raw = self.rfile.read(length)
                return json.loads(raw.decode("utf-8"))

            def _check_auth(self) -> bool:
                token = self.headers.get("X-Auth-Token", "")
                return secrets.compare_digest(token, server._auth_token)

            def _check_csrf(self) -> bool:
                token = self.headers.get("X-CSRF-Token", "")
                return secrets.compare_digest(token, server._csrf_token)

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:" + str(server.port))
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Auth-Token, X-CSRF-Token")
                self.end_headers()

            def do_GET(self):
                parsed = urlparse(self.path)

                if parsed.path == "/":
                    html = HTML_PAGE.replace("__CSRF_TOKEN__", server._csrf_token)
                    html = html.replace("__AUTH_TOKEN__", server._auth_token)
                    self._send_html(html)
                    self._log_audit("GET", "/", 200)

                elif parsed.path == "/api/config":
                    if not self._check_auth():
                        self._send_json({"error": "Unauthorized."}, 401)
                        self._log_audit("GET", "/api/config", 401)
                        return

                    env = server._load_env()
                    channels_str = env.get("YOUTUBE_CHANNEL_IDS", "")
                    channels = [c.strip() for c in channels_str.split(",") if c.strip()] if channels_str else []
                    try:
                        freq = int(env.get("SCHEDULE_FREQUENCY_HOURS", "6"))
                    except ValueError:
                        freq = 6
                    self._send_json({
                        "telegram_bot_token": _mask_token(env["TELEGRAM_BOT_TOKEN"]),
                        "telegram_chat_id": env["TELEGRAM_CHAT_ID"],
                        "telegram_bot_username": env["TELEGRAM_BOT_USERNAME"],
                        "ollama_host": env["OLLAMA_HOST"],
                        "ollama_model": env["OLLAMA_MODEL"],
                        "youtube_channel_ids": channels,
                        "schedule_frequency_hours": freq,
                        "schedule_start_time": env["SCHEDULE_START_TIME"],
                        "youtube_api_key": _mask_token(env["YOUTUBE_API_KEY"]),
                    })
                    self._log_audit("GET", "/api/config", 200)

                else:
                    self.send_error(404)
                    self._log_audit("GET", parsed.path, 404)

            def do_POST(self):
                parsed = urlparse(self.path)

                if not self._check_auth():
                    self._send_json({"error": "Unauthorized."}, 401)
                    self._log_audit("POST", parsed.path, 401)
                    return

                if not self._check_csrf():
                    self._send_json({"error": "CSRF token invalid."}, 403)
                    self._log_audit("POST", parsed.path, 403)
                    return

                if parsed.path == "/api/channels/add":
                    body = self._read_body()
                    url = body.get("url", "").strip()
                    if not url:
                        self._send_json({"error": "No URL provided."}, 400)
                        self._log_audit("POST", "/api/channels/add", 400)
                        return

                    channel_id = server._wizard.extract_channel_id_from_url(url)
                    if not channel_id:
                        self._send_json({"error": "Could not extract channel ID from this URL. Please check the URL and try again."}, 400)
                        self._log_audit("POST", "/api/channels/add", 400)
                        return

                    if not server._wizard.is_valid_channel_id(channel_id):
                        self._send_json({"error": f"Invalid channel ID format: {channel_id}. Must start with 'UC' and be 24 characters."}, 400)
                        self._log_audit("POST", "/api/channels/add", 400)
                        return

                    env = server._load_env()
                    channels_str = env.get("YOUTUBE_CHANNEL_IDS", "")
                    channels = [c.strip() for c in channels_str.split(",") if c.strip()] if channels_str else []

                    if channel_id in channels:
                        self._send_json({"error": "Channel already in your list."}, 409)
                        self._log_audit("POST", "/api/channels/add", 409)
                        return
                    if len(channels) >= 100:
                        self._send_json({"error": "Maximum of 100 channels reached."}, 400)
                        self._log_audit("POST", "/api/channels/add", 400)
                        return

                    channels.append(channel_id)
                    server._save_env({"YOUTUBE_CHANNEL_IDS": ",".join(channels)})
                    self._send_json({"success": True, "channel_id": channel_id, "channels": channels})
                    self._log_audit("POST", "/api/channels/add", 200)

                elif parsed.path == "/api/channels/delete":
                    body = self._read_body()
                    channel_id = body.get("channel_id", "").strip()
                    if not channel_id:
                        self._send_json({"error": "No channel ID provided."}, 400)
                        self._log_audit("POST", "/api/channels/delete", 400)
                        return

                    env = server._load_env()
                    channels_str = env.get("YOUTUBE_CHANNEL_IDS", "")
                    channels = [c.strip() for c in channels_str.split(",") if c.strip()] if channels_str else []

                    if channel_id not in channels:
                        self._send_json({"error": "Channel not found in list."}, 404)
                        self._log_audit("POST", "/api/channels/delete", 404)
                        return

                    channels.remove(channel_id)
                    server._save_env({"YOUTUBE_CHANNEL_IDS": ",".join(channels)})
                    self._send_json({"success": True, "channels": channels})
                    self._log_audit("POST", "/api/channels/delete", 200)

                elif parsed.path == "/api/frequency":
                    body = self._read_body()
                    freq = body.get("frequency")
                    if freq is None:
                        self._send_json({"error": "No frequency value provided."}, 400)
                        self._log_audit("POST", "/api/frequency", 400)
                        return
                    try:
                        freq = int(freq)
                    except (ValueError, TypeError):
                        self._send_json({"error": "Frequency must be a number."}, 400)
                        self._log_audit("POST", "/api/frequency", 400)
                        return
                    if freq < 1 or freq > 24:
                        self._send_json({"error": "Frequency must be between 1 and 24."}, 400)
                        self._log_audit("POST", "/api/frequency", 400)
                        return

                    server._save_env({"SCHEDULE_FREQUENCY_HOURS": str(freq)})
                    self._send_json({"success": True, "frequency": freq})
                    self._log_audit("POST", "/api/frequency", 200)

                elif parsed.path == "/api/ollama":
                    body = self._read_body()
                    host = body.get("ollama_host", "").strip()
                    model = body.get("ollama_model", "").strip()

                    if not host:
                        self._send_json({"error": "Ollama host is required."}, 400)
                        self._log_audit("POST", "/api/ollama", 400)
                        return
                    if not host.startswith(("http://", "https://")):
                        self._send_json({"error": "Ollama host must start with http:// or https://"}, 400)
                        self._log_audit("POST", "/api/ollama", 400)
                        return

                    updates = {"OLLAMA_HOST": host}
                    if model:
                        updates["OLLAMA_MODEL"] = model

                    server._save_env(updates)
                    self._send_json({"success": True})
                    self._log_audit("POST", "/api/ollama", 200)

                elif parsed.path == "/api/youtube-api-key":
                    body = self._read_body()
                    key = body.get("youtube_api_key", "").strip()
                    server._save_env({"YOUTUBE_API_KEY": key})
                    self._send_json({"success": True})
                    self._log_audit("POST", "/api/youtube-api-key", 200)

                elif parsed.path == "/api/telegram":
                    body = self._read_body()
                    token = body.get("bot_token", "").strip()
                    chat_id = body.get("chat_id", "").strip()
                    username = body.get("username", "").strip()

                    if not token or not chat_id:
                        self._send_json({"error": "Bot token and chat ID are required."}, 400)
                        self._log_audit("POST", "/api/telegram", 400)
                        return

                    import re
                    if not re.match(r'^\d+:[A-Za-z0-9_-]+$', token):
                        self._send_json({"error": "Invalid bot token format. Expected: 123456789:ABCdef..."}, 400)
                        self._log_audit("POST", "/api/telegram", 400)
                        return
                    if not chat_id.isdigit():
                        self._send_json({"error": "Chat ID must be a number."}, 400)
                        self._log_audit("POST", "/api/telegram", 400)
                        return

                    updates = {
                        "TELEGRAM_BOT_TOKEN": token,
                        "TELEGRAM_CHAT_ID": chat_id,
                    }
                    if username:
                        updates["TELEGRAM_BOT_USERNAME"] = username

                    server._save_env(updates)
                    self._send_json({"success": True})
                    self._log_audit("POST", "/api/telegram", 200)

                elif parsed.path == "/api/save":
                    body = self._read_body()
                    updates = {}

                    if "youtube_channel_ids" in body:
                        channels = body.get("youtube_channel_ids", [])
                        if isinstance(channels, list):
                            updates["YOUTUBE_CHANNEL_IDS"] = ",".join(channels)

                    if "schedule_frequency_hours" in body:
                        freq = body.get("schedule_frequency_hours")
                        try:
                            freq = int(freq)
                            if 1 <= freq <= 24:
                                updates["SCHEDULE_FREQUENCY_HOURS"] = str(freq)
                        except (ValueError, TypeError):
                            pass

                    ollama_host = body.get("ollama_host", "").strip()
                    ollama_model = body.get("ollama_model", "").strip()
                    if ollama_host:
                        updates["OLLAMA_HOST"] = ollama_host
                    if ollama_model:
                        updates["OLLAMA_MODEL"] = ollama_model

                    api_key = body.get("youtube_api_key", "").strip()
                    if api_key and not api_key.startswith("***"):
                        updates["YOUTUBE_API_KEY"] = api_key

                    token = body.get("telegram_bot_token", "").strip()
                    chat_id = body.get("telegram_chat_id", "").strip()
                    username = body.get("telegram_bot_username", "").strip()

                    if token and not token.startswith("***"):
                        updates["TELEGRAM_BOT_TOKEN"] = token
                    if chat_id:
                        updates["TELEGRAM_CHAT_ID"] = chat_id
                    if username:
                        updates["TELEGRAM_BOT_USERNAME"] = username

                    if updates:
                        server._save_env(updates)
                    self._send_json({"success": True})
                    self._log_audit("POST", "/api/save", 200)

                else:
                    self.send_error(404)
                    self._log_audit("POST", parsed.path, 404)

        return Handler

    def serve(self):
        handler = self._make_handler()
        # Bind to localhost only — not accessible from network
        httpd = HTTPServer(("127.0.0.1", self.port), handler)
        url = f"http://127.0.0.1:{self.port}"
        print("=" * 60)
        print("Web setup server running at:", url)
        print("Server is bound to localhost (127.0.0.1) only.")
        print(f"Config directory: {self.config_dir}")
        print("=" * 60)
        print()
        print("AUTH TOKEN (required for all API requests):")
        print(f"  {self._auth_token}")
        print()
        print("Open this URL in your browser to begin setup.")
        print("The auth token is embedded in the page automatically.")
        print()
        print("Press Ctrl+C to stop the server.")
        print("=" * 60)
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            httpd.server_close()


def main():
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    server = WebSetupServer(port=port)
    server.serve()


if __name__ == "__main__":
    main()
