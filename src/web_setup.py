import os
import sys
import json
import webbrowser
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv, set_key

from setup import SetupWizard


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ytube Summarier - Setup</title>
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
</style>
</head>
<body>

<h1>Ytube Summarier</h1>

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
var state = {
    channels: [],
    frequency: 6,
    telegram: { token: '', chat_id: '', username: '' }
};

function init() {
    fetch('/api/config')
    .then(function(r) { return r.json(); })
    .then(function(data) {
        state.channels = data.youtube_channel_ids || [];
        state.frequency = data.schedule_frequency_hours || 6;
        state.telegram = {
            token: data.telegram_bot_token || '',
            chat_id: data.telegram_chat_id || '',
            username: data.telegram_bot_username || ''
        };
        document.getElementById('freq-input').value = state.frequency;
        renderChannels();
        renderTelegramFields();
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
        headers: {'Content-Type': 'application/json'},
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
        headers: {'Content-Type': 'application/json'},
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
        headers: {'Content-Type': 'application/json'},
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
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({chat_id: chatId, username: username, bot_token: token})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            alert(data.error);
        } else {
            state.telegram.chat_id = chatId;
            state.telegram.username = username;
            state.telegram.token = token;
            renderTelegramFields();
            closeTelegramDialog();
        }
    });
}

function saveAll() {
    fetch('/api/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            youtube_channel_ids: state.channels,
            schedule_frequency_hours: state.frequency,
            telegram_chat_id: state.telegram.chat_id,
            telegram_bot_username: state.telegram.username,
            telegram_bot_token: state.telegram.token
        })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            showStatus('save-status', data.error, true);
        } else {
            showStatus('save-status', 'Configuration saved successfully!', false);
        }
    });
}

document.getElementById('channel-url').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') addChannel();
});

init();
</script>

</body>
</html>"""


class WebSetupServer:
    """Browser-based setup server for YouTube Summarizer."""

    def __init__(self, port=8080):
        self.port = port
        self.project_root = Path(__file__).parent.parent
        self.env_file = self.project_root / ".env"
        self._wizard = SetupWizard()

    def _load_env(self) -> dict:
        if self.env_file.exists():
            load_dotenv(self.env_file, override=True)
        return {
            "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
            "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", ""),
            "TELEGRAM_BOT_USERNAME": os.getenv("TELEGRAM_BOT_USERNAME", ""),
            "OLLAMA_HOST": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            "YOUTUBE_CHANNEL_IDS": os.getenv("YOUTUBE_CHANNEL_IDS", ""),
            "SCHEDULE_FREQUENCY_HOURS": os.getenv("SCHEDULE_FREQUENCY_HOURS", "6"),
            "SCHEDULE_START_TIME": os.getenv("SCHEDULE_START_TIME", ""),
        }

    def _save_env(self, updates: dict):
        env_path = str(self.env_file)
        if not self.env_file.exists():
            self.env_file.touch()
        for key, value in updates.items():
            set_key(env_path, key, str(value))

    def _make_handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def _send_json(self, data, status=200):
                body = json.dumps(data).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
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

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/":
                    self._send_html(HTML_PAGE)
                elif parsed.path == "/api/config":
                    env = server._load_env()
                    channels_str = env.get("YOUTUBE_CHANNEL_IDS", "")
                    channels = [c.strip() for c in channels_str.split(",") if c.strip()] if channels_str else []
                    try:
                        freq = int(env.get("SCHEDULE_FREQUENCY_HOURS", "6"))
                    except ValueError:
                        freq = 6
                    self._send_json({
                        "telegram_bot_token": env["TELEGRAM_BOT_TOKEN"],
                        "telegram_chat_id": env["TELEGRAM_CHAT_ID"],
                        "telegram_bot_username": env["TELEGRAM_BOT_USERNAME"],
                        "ollama_host": env["OLLAMA_HOST"],
                        "ollama_model": env["OLLAMA_MODEL"],
                        "youtube_channel_ids": channels,
                        "schedule_frequency_hours": freq,
                        "schedule_start_time": env["SCHEDULE_START_TIME"],
                    })
                else:
                    self.send_error(404)

            def do_POST(self):
                parsed = urlparse(self.path)

                if parsed.path == "/api/channels/add":
                    body = self._read_body()
                    url = body.get("url", "").strip()
                    if not url:
                        self._send_json({"error": "No URL provided."}, 400)
                        return

                    channel_id = server._wizard.extract_channel_id_from_url(url)
                    if not channel_id:
                        self._send_json({"error": "Could not extract channel ID from this URL. Please check the URL and try again."}, 400)
                        return

                    if not server._wizard.is_valid_channel_id(channel_id):
                        self._send_json({"error": f"Invalid channel ID format: {channel_id}. Must start with 'UC' and be 24 characters."}, 400)
                        return

                    env = server._load_env()
                    channels_str = env.get("YOUTUBE_CHANNEL_IDS", "")
                    channels = [c.strip() for c in channels_str.split(",") if c.strip()] if channels_str else []

                    if channel_id in channels:
                        self._send_json({"error": "Channel already in your list."}, 409)
                        return
                    if len(channels) >= 100:
                        self._send_json({"error": "Maximum of 100 channels reached."}, 400)
                        return

                    channels.append(channel_id)
                    server._save_env({"YOUTUBE_CHANNEL_IDS": ",".join(channels)})
                    self._send_json({"success": True, "channel_id": channel_id, "channels": channels})

                elif parsed.path == "/api/channels/delete":
                    body = self._read_body()
                    channel_id = body.get("channel_id", "").strip()
                    if not channel_id:
                        self._send_json({"error": "No channel ID provided."}, 400)
                        return

                    env = server._load_env()
                    channels_str = env.get("YOUTUBE_CHANNEL_IDS", "")
                    channels = [c.strip() for c in channels_str.split(",") if c.strip()] if channels_str else []

                    if channel_id not in channels:
                        self._send_json({"error": "Channel not found in list."}, 404)
                        return

                    channels.remove(channel_id)
                    server._save_env({"YOUTUBE_CHANNEL_IDS": ",".join(channels)})
                    self._send_json({"success": True, "channels": channels})

                elif parsed.path == "/api/frequency":
                    body = self._read_body()
                    freq = body.get("frequency")
                    if freq is None:
                        self._send_json({"error": "No frequency value provided."}, 400)
                        return
                    try:
                        freq = int(freq)
                    except (ValueError, TypeError):
                        self._send_json({"error": "Frequency must be a number."}, 400)
                        return
                    if freq < 1 or freq > 24:
                        self._send_json({"error": "Frequency must be between 1 and 24."}, 400)
                        return

                    server._save_env({"SCHEDULE_FREQUENCY_HOURS": str(freq)})
                    self._send_json({"success": True, "frequency": freq})

                elif parsed.path == "/api/telegram":
                    body = self._read_body()
                    token = body.get("bot_token", "").strip()
                    chat_id = body.get("chat_id", "").strip()
                    username = body.get("username", "").strip()

                    if not token or not chat_id:
                        self._send_json({"error": "Bot token and chat ID are required."}, 400)
                        return

                    import re
                    if not re.match(r'^\d+:[A-Za-z0-9_-]+$', token):
                        self._send_json({"error": "Invalid bot token format. Expected: 123456789:ABCdef..."}, 400)
                        return
                    if not chat_id.isdigit():
                        self._send_json({"error": "Chat ID must be a number."}, 400)
                        return

                    updates = {
                        "TELEGRAM_BOT_TOKEN": token,
                        "TELEGRAM_CHAT_ID": chat_id,
                    }
                    if username:
                        updates["TELEGRAM_BOT_USERNAME"] = username

                    server._save_env(updates)
                    self._send_json({"success": True})

                elif parsed.path == "/api/save":
                    body = self._read_body()
                    updates = {}

                    channels = body.get("youtube_channel_ids", [])
                    if isinstance(channels, list):
                        updates["YOUTUBE_CHANNEL_IDS"] = ",".join(channels)

                    freq = body.get("schedule_frequency_hours")
                    if freq is not None:
                        try:
                            freq = int(freq)
                            if 1 <= freq <= 24:
                                updates["SCHEDULE_FREQUENCY_HOURS"] = str(freq)
                        except (ValueError, TypeError):
                            pass

                    token = body.get("telegram_bot_token", "").strip()
                    chat_id = body.get("telegram_chat_id", "").strip()
                    username = body.get("telegram_bot_username", "").strip()

                    if token:
                        updates["TELEGRAM_BOT_TOKEN"] = token
                    if chat_id:
                        updates["TELEGRAM_CHAT_ID"] = chat_id
                    if username:
                        updates["TELEGRAM_BOT_USERNAME"] = username

                    if updates:
                        server._save_env(updates)
                    self._send_json({"success": True})

                else:
                    self.send_error(404)

        return Handler

    def serve(self):
        handler = self._make_handler()
        httpd = HTTPServer(("127.0.0.1", self.port), handler)
        url = f"http://127.0.0.1:{self.port}"
        print(f"Web setup server running at: {url}")
        print("Opening browser automatically. Press Ctrl+C to stop.")
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
