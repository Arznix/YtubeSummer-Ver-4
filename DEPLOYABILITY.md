# Deployability Guide

This document describes the deployment options, considerations, and best practices for the YouTube Summarizer program.

---

## Introduction: Why Deployability Matters

### The Problem with "It Works on My Machine"

Every programmer has experienced this moment. You spend hours writing code on your laptop. You test it. It works perfectly. You send it to a friend or try to run it on a different computer, and suddenly everything breaks. The program cannot find the right files. The settings are wrong. A required library is missing. You spend another few hours just figuring out how to get it running on the new machine, and you have not even started fixing bugs or adding features yet.

This is the deployability problem. **Deployability** is the ability to take a piece of software from the place where it was built and successfully run it somewhere else — on another person's computer, on a server, or in a different environment — without having to rewrite large parts of it. A program that is easy to deploy can be set up and running in minutes. A program that is hard to deploy might take hours, days, or might simply never work at all on a new machine.

Think of it like cooking a meal versus opening a box of instant noodles. If you cook a meal from scratch, it might taste wonderful in your own kitchen because you know exactly where everything is and how your stove works. But if you try to cook that same meal in someone else's kitchen, you might not find the right pan, the oven might work differently, and the spices you need might not be there. Instant noodles, on the other hand, work anywhere: you just need hot water. The instructions are written so that anyone, anywhere, can follow them and get a working meal. Deployability is about making your software more like the instant noodles — reliable, predictable, and easy to set up no matter where it ends up.

For this project, deployability is especially important because the YouTube Summarizer is designed to be used by people who are not professional programmers. It is a tool that regular users should be able to install, configure, and run without needing to understand the code underneath. If the setup process is confusing or fragile, people will give up and never use the program, no matter how good the underlying technology is.

### What the Kaggle Course Teaches About Going from Prototype to Production

The Kaggle 5-Day AI Agents Intensive Course with Google dedicates its entire final day — **Day 5: Prototype to Production** — to this exact problem. The course teaches that building a working prototype is only about half the journey. The other half is turning that prototype into something that other people can actually use, that runs reliably without constant supervision, and that can be updated and maintained over time.

The course identifies several key concepts that separate a prototype from a production-ready system. The first is **observability**. A prototype runs silently and breaks silently — you have no idea what it is doing or why it stopped working. A production system logs its actions, records errors, and provides health checks so you can see at a glance whether it is running correctly. The second concept is **governance**. A prototype has no rules about who can change it or how changes are made. A production system has clear procedures for updates, rollbacks, and configuration management. The third concept is **scalability**. A prototype might work for one person but fall apart if a hundred people try to use it. A production system is designed to handle growth gracefully.

The course also emphasizes what it calls the "vibe to live" transition — moving from a rough, personal prototype (the "vibe" version that works for you) to a real, live system that works for everyone. This transition requires thinking about things that you do not worry about in a prototype: how does the system start automatically when the computer boots? How do you update it without breaking it? How do you back up its data? How do you debug it when something goes wrong?

### Why We Chose the Deployability Concepts in This Document

When we looked at this project through the lens of the Kaggle course and the SAIF security framework, we identified several deployability gaps that needed to be addressed. The sections that follow in this document were not chosen randomly — each one solves a specific problem that would prevent this program from being useful to real users.

**The first problem was configuration management.** A prototype developer might hardcode settings or edit files directly, but regular users need a guided setup process. This led to the creation of the interactive setup wizard (`python src/setup.py`) and the browser-based web setup (`python src/setup.py --web`). These tools walk users through configuration step by step, validate their inputs, and save settings to a `.env` file without requiring them to touch a text editor. This is the "harmonize platform controls" principle from SAIF — making sure that every user has a consistent, validated configuration experience.

**The second problem was reliability.** A prototype runs once and stops. A production system needs to run continuously, recover from crashes, and restart automatically if the computer reboots. This led to the deployment scripts for Windows (using NSSM), Linux (using systemd), and macOS (using LaunchAgent). These scripts make the program start automatically, restart if it crashes, and log its output so problems can be diagnosed. This is the "adapt controls with faster feedback loops" principle from SAIF — building systems that detect and recover from failures automatically.

**The third problem was maintainability.** A prototype does not need update procedures because the developer just rewrites whatever changed. A production system needs a clear process for receiving updates without breaking existing configurations. This led to the update procedures section, which describes how to pull new code, preserve your `.env` file, and restart the service cleanly. The automated update script is designed so that a single command handles the entire process — stopping the service, backing up configuration, pulling changes, installing dependencies, and restarting.

**The fourth problem was observability.** A prototype might print errors to the screen and hope someone notices. A production system needs structured logging, log rotation, and health checks so that problems are visible before they become critical. This led to the monitoring and logging section, which describes how to check process status, verify Ollama connectivity, and monitor the database. The systemd service configuration includes automatic log management so that log files do not grow unboundedly and fill up the disk.

**The fifth problem was data safety.** A prototype does not worry about data loss because the developer has the source code and can start over. A production system stores user configurations, database state, and processing history that cannot be easily recreated. This led to the backup and recovery section, which describes what files to back up, how to automate backups, and how to restore from a backup if something goes wrong.

**The sixth problem was performance.** A prototype does not need to be fast because it runs once for testing. A production system runs repeatedly and needs to be efficient. This led to the performance optimization section, which covers database maintenance (vacuuming, indexing), log rotation (preventing disk space exhaustion), and memory management (limiting cache sizes for constrained environments).

### How These Concepts Connect

All six of these problems — configuration, reliability, maintainability, observability, data safety, and performance — are connected. A system that is hard to configure is hard to maintain. A system without observability cannot be diagnosed when it fails. A system without backup procedures puts user data at risk. A system without performance limits can crash under load. The Kaggle course teaches that production readiness is not about solving one problem well — it is about addressing the entire lifecycle of a deployed system, from initial setup through daily operation to eventual updates and recovery.

The SAIF framework reinforces this idea. Its principle of "harmonize platform controls" means that security, reliability, and deployability should not be separate concerns handled by separate teams. They should be woven into every part of the system. When we added the web setup server, we did not just make it work — we made it bind to localhost, require authentication, log all requests, and mask sensitive data. When we added deployment scripts, we did not just make the program start — we made it restart on failure, log its output, and clean up old logs.

The deployment options described in this document — local desktop, headless server, Docker container, systemd service — are not arbitrary choices. Each one addresses a specific user need: personal use on a laptop, always-on operation on a server, reproducible deployment in containers, and automatic startup on Linux. Each one follows the same patterns: configure with environment variables, deploy with scripts, monitor with logs, and maintain with update procedures.

By the time you finish reading this document, you will understand not just *how* to deploy this program, but *why* each deployment pattern exists and what problem it solves. That understanding is what turns a collection of deployment commands into a coherent deployment strategy.

---

### 1. Local Desktop Deployment (Recommended)

**Best for**: Personal use, single user

**Requirements**:
- Windows 10/11, macOS 10.15+, or Linux
- Python 3.8+
- Ollama installed locally
- Internet connection

**Deployment Steps**:
```bash
# 1. Clone repository
git clone https://github.com/Arznix/youtube-summarizer.git
cd youtube-summarizer

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
copy .env.example .env
# Edit .env with your settings

# 5. Run
python src/agent_orchestrator.py
```

**Advantages**:
- Simple setup
- No server maintenance
- Full control over data
- No recurring costs

**Limitations**:
- Only runs when computer is on
- Single user only
- Limited by local hardware

---

### 2. Headless Server Deployment

**Best for**: Always-on operation, single user

**Requirements**:
- Linux server (Ubuntu 20.04+)
- SSH access
- Python 3.8+
- Ollama installed

**Deployment Steps**:

```bash
# 1. Connect to server
ssh user@server-ip

# 2. Install dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv git

# 3. Clone repository
git clone https://github.com/Arznix/youtube-summarizer.git
cd youtube-summarizer

# 4. Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:1.5b

# 6. Configure
cp .env.example .env
nano .env  # Edit with your settings

# 7. Run as background service
nohup python3 src/agent_orchestrator.py > logs/scheduler.log 2>&1 &
```

**Advantages**:
- Always running
- No local computer needed
- Remote access possible

**Limitations**:
- Requires server management
- Network configuration needed
- Security considerations

---

### 3. Docker Deployment

**Best for**: Containerized environments, easy replication

**Requirements**:
- Docker installed
- Docker Compose (optional)

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create .env from example if not exists
RUN cp .env.example .env

# Expose no ports (runs as daemon)
# Volumes for persistent data
VOLUME ["/app/data", "/app/.env"]

# Run the application
CMD ["python", "src/agent_orchestrator.py"]
```

**Docker Compose** (`docker-compose.yml`):
```yaml
version: '3.8'

services:
  youtube-summarizer:
    build: .
    container_name: youtube-summarizer
    restart: unless-stopped
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env
    environment:
      - TZ=UTC
    networks:
      - app-network

  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    networks:
      - app-network

volumes:
  ollama_data:

networks:
  app-network:
    driver: bridge
```

**Deployment Steps**:
```bash
# 1. Build and start
docker-compose up -d

# 2. Pull Ollama model
docker exec -it ollama ollama pull qwen2.5:1.5b

# 3. View logs
docker-compose logs -f youtube-summarizer

# 4. Stop
docker-compose down
```

**Advantages**:
- Consistent environment
- Easy to replicate
- Isolated from host
- Simple updates

**Limitations**:
- Requires Docker knowledge
- Additional overhead
- Ollama in Docker may have GPU limitations

---

### 4. Cloud VM Deployment

**Best for**: Scalable, production-like environments

**Supported Providers**:
- AWS EC2
- Google Cloud Compute Engine
- Azure Virtual Machines
- DigitalOcean Droplets
- Linode

**Example (AWS EC2)**:

```bash
# 1. Launch EC2 instance
# - AMI: Ubuntu 22.04 LTS
# - Instance type: t3.medium (2 vCPU, 4GB RAM)
# - Security group: Allow SSH (22), Ollama (11434)

# 2. Connect
ssh -i key.pem ubuntu@ec2-ip

# 3. Install dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

# 4. Follow headless server deployment steps

# 5. Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 11434/tcp  # Ollama (if remote access needed)
sudo ufw enable
```

**Advantages**:
- Scalable resources
- High availability
- Professional infrastructure
- Backup options

**Limitations**:
- Recurring costs
- Complex configuration
- Security management
- Network latency

---

### 5. Raspberry Pi Deployment

**Best for**: Low-cost, always-on home server

**Requirements**:
- Raspberry Pi 4 (4GB+ RAM)
- Raspberry Pi OS (64-bit)
- Internet connection

**Deployment Steps**:

```bash
# 1. Setup Raspberry Pi OS
# - Flash SD card with 64-bit OS
# - Enable SSH
# - Connect to network

# 2. Update system
sudo apt update && sudo apt upgrade -y

# 3. Install dependencies
sudo apt install -y python3 python3-pip python3-venv git

# 4. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 5. Pull model
ollama pull qwen2.5:1.5b

# 6. Clone and setup project
git clone https://github.com/Arznix/youtube-summarizer.git
cd youtube-summarizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 7. Configure
cp .env.example .env
nano .env

# 8. Run
python3 src/agent_orchestrator.py
```

**Advantages**:
- Low cost (~$50-100)
- Low power consumption
- Always-on capable
- Educational

**Limitations**:
- Limited performance
- SD card reliability
- Memory constraints

---

## Deployment Considerations

### 1. Resource Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 4 GB | 8+ GB |
| **Storage** | 10 GB | 50+ GB |
| **Network** | 1 Mbps | 10+ Mbps |

### 2. Ollama Considerations

**Local vs Remote Ollama**:

```env
# Local Ollama (same machine)
OLLAMA_HOST=http://localhost:11434

# Remote Ollama (different machine)
OLLAMA_HOST=http://192.168.1.100:11434
```

**GPU Acceleration**:
- Ollama supports NVIDIA GPUs
- Requires CUDA drivers
- Significantly faster processing

**Model Selection**:
```env
# Fast, low resource (1.5B parameters)
OLLAMA_MODEL=qwen2.5:1.5b

# Better quality, higher resource (7B parameters)
OLLAMA_MODEL=qwen2.5:1.5b
```

### 3. Network Configuration

**Firewall Rules**:
```bash
# Linux (ufw)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 11434/tcp   # Ollama (if remote)

# Windows Firewall
netsh advfirewall firewall add rule name="Ollama" dir=in action=allow protocol=TCP localport=11434
```

**Port Forwarding** (for remote access):
- Forward port 11434 to Ollama server
- Use HTTPS with reverse proxy for security

### 4. Security Considerations

**Network Security**:
- Use HTTPS for all external connections
- Implement IP whitelisting
- Use VPN for remote access
- Regular security updates

**Credential Management**:
- Use environment variables
- Never commit `.env` files
- Rotate credentials regularly
- Use secrets management for production

**Web Setup Server Security**:
- Server binds to localhost only (`127.0.0.1`)
- Auth token required for all API requests
- CSRF protection for all POST requests
- Bot token masked in browser UI
- All requests logged to `web_setup.log` with timestamp, IP, and status

### 5. Monitoring and Logging

**Log Files**:
```bash
# Application logs
tail -f orchestrator.log

# System logs (systemd)
journalctl -u youtube-summarizer -f
```

**Health Checks**:
```bash
# Check if process is running
ps aux | grep agent_orchestrator

# Check Ollama status
curl http://localhost:11434/api/tags

# Check database
sqlite3 data/subscriptions_state.db "SELECT COUNT(*) FROM videos;"
```

### 6. Backup and Recovery

**What to Backup**:
```bash
# Configuration
cp .env .env.backup

# Database
cp data/subscriptions_state.db data/backup/

# Logs (optional)
tar -czf logs-$(date +%Y%m%d).tar.gz logs/
```

**Automated Backup Script**:
```bash
#!/bin/bash
BACKUP_DIR="/backup/youtube-summarizer"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR
cp .env $BACKUP_DIR/.env.$DATE
cp data/subscriptions_state.db $BACKUP_DIR/db.$DATE

# Keep only last 7 days
find $BACKUP_DIR -name "*.env.*" -mtime +7 -delete
find $BACKUP_DIR -name "db.*" -mtime +7 -delete
```

---

## Deployment Scripts

### Windows Service (NSSM)

```bash
# Install NSSM (Non-Sucking Service Manager)
# Download from https://nssm.cc/download

# Install as Windows service
nssm install YouTubeSummarizer "C:\Python39\python.exe" "C:\path\to\src\agent_orchestrator.py"
nssm set YouTubeSummarizer AppDirectory "C:\path\to\youtube-summarizer"
nssm set YouTubeSummarizer DisplayName "YouTube Summarizer"
nssm set YouTubeSummarizer Description "YouTube video summarization service"
nssm set YouTubeSummarizer Start SERVICE_AUTO_START

# Start service
nssm start YouTubeSummarizer

# View logs
nssm logs YouTubeSummarizer
```

### Linux Systemd Service

```ini
# /etc/systemd/system/youtube-summarizer.service

[Unit]
Description=YouTube Summarizer Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/youtube-summarizer
ExecStart=/home/ubuntu/youtube-summarizer/venv/bin/python src/agent_orchestrator.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable youtube-summarizer
sudo systemctl start youtube-summarizer

# Check status
sudo systemctl status youtube-summarizer

# View logs
sudo journalctl -u youtube-summarizer -f
```

### macOS LaunchAgent

```xml
<!-- ~/Library/LaunchAgents/com.youtube.summarizer.plist -->

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.youtube.summarizer</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/username/youtube-summarizer/src/agent_orchestrator.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/username/youtube-summarizer</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/username/youtube-summarizer/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/username/youtube-summarizer/logs/stderr.log</string>
</dict>
</plist>
```

```bash
# Load the agent
launchctl load ~/Library/LaunchAgents/com.youtube.summarizer.plist

# Unload the agent
launchctl unload ~/Library/LaunchAgents/com.youtube.summarizer.plist
```

---

## Update Procedures

### Manual Update

```bash
# 1. Stop the service
sudo systemctl stop youtube-summarizer  # Linux
nssm stop YouTubeSummarizer  # Windows

# 2. Backup configuration
cp .env .env.backup

# 3. Pull updates
git pull origin master

# 4. Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# 5. Restart service
sudo systemctl start youtube-summarizer  # Linux
nssm start YouTubeSummarizer  # Windows
```

### Automated Update Script

```bash
#!/bin/bash
# update.sh

set -e

echo "Updating YouTube Summarizer..."

# Stop service
sudo systemctl stop youtube-summarizer

# Backup
cp .env .env.backup.$(date +%Y%m%d)

# Pull changes
git pull origin master

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Start service
sudo systemctl start youtube-summarizer

echo "Update complete!"
```

---

## Performance Optimization

### 1. Database Optimization

```bash
# Vacuum database periodically
sqlite3 data/subscriptions_state.db "VACUUM;"

# Add indexes for better performance
sqlite3 data/subscriptions_state.db "
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_video_id ON videos(video_id);
"
```

### 2. Log Rotation

```bash
# /etc/logrotate.d/youtube-summarizer

/home/ubuntu/youtube-summarizer/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
}
```

### 3. Memory Management

```python
# In config.py
MAX_CHANNELS = 50  # Reduce if memory limited
TRANSCRIPT_CACHE_SIZE = 100  # Limit cache size
```

---

## Troubleshooting Deployments

### Common Issues

| Issue | Solution |
|-------|----------|
| Service won't start | Check logs, verify Python path |
| Ollama connection refused | Ensure Ollama is running, check firewall |
| Permission denied | Check file ownership, use sudo |
| Out of memory | Reduce channels, use smaller model |
| Database locked | Stop other instances, check permissions |

### Debug Mode

```bash
# Run with verbose logging
PYTHONUNBUFFERED=1 python src/agent_orchestrator.py --once

# Check environment variables
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.environ)"
```

### Health Check Script

```bash
#!/bin/bash
# healthcheck.sh

# Check if process is running
if ! pgrep -f "agent_orchestrator" > /dev/null; then
    echo "ERROR: YouTube Summarizer not running"
    exit 1
fi

# Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "ERROR: Ollama not responding"
    exit 1
fi

# Check database
if ! sqlite3 data/subscriptions_state.db "SELECT 1;" > /dev/null; then
    echo "ERROR: Database not accessible"
    exit 1
fi

echo "All checks passed"
exit 0
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] System meets minimum requirements
- [ ] Python 3.8+ installed
- [ ] Ollama installed and running
- [ ] AI model downloaded
- [ ] Network connectivity verified
- [ ] Firewall rules configured
- [ ] Credentials prepared

### Deployment

- [ ] Repository cloned
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Configuration file created
- [ ] Telegram bot configured
- [ ] YouTube channels added
- [ ] Schedule configured
- [ ] Web setup tested (`python src/setup.py --web`)
- [ ] Web setup security verified (localhost binding, auth token)

### Post-Deployment

- [ ] Test run completed (`--once`)
- [ ] Telegram notifications working
- [ ] Logs being generated
- [ ] Service auto-starts on boot
- [ ] Monitoring configured
- [ ] Backup schedule set

---

## Cost Considerations

### Free Tier (Local)

| Component | Cost |
|-----------|------|
| Python | Free |
| Ollama | Free |
| Telegram Bot | Free |
| YouTube RSS | Free |
| **Total** | **$0** |

### Cloud Deployment (Estimated)

| Provider | Instance | Monthly Cost |
|----------|----------|--------------|
| AWS EC2 | t3.medium | ~$30 |
| Google Cloud | e2-medium | ~$25 |
| Azure | B2s | ~$30 |
| DigitalOcean | 2GB Droplet | ~$12 |
| Linode | 2GB | ~$10 |

---

## Conclusion

The YouTube Summarizer is designed for **easy local deployment** but can be deployed in various environments:

- **Simplest**: Local desktop (personal use)
- **Most Reliable**: Headless Linux server (always-on)
- **Most Portable**: Docker (consistent environment)
- **Most Scalable**: Cloud VM (production)
- **Most Affordable**: Raspberry Pi (home server)

**Recommended for beginners**: Local desktop deployment
**Recommended for production**: Headless Linux server with systemd

---

*Last updated: 2026-06-21*
