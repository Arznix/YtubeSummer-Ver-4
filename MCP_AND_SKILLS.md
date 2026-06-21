# MCP Concepts and Agent Skills

This document explains how Model Context Protocol (MCP) concepts and Agent Skills are demonstrated and incorporated into the YouTube Summarizer program.

---

## Overview

The YouTube Summarizer implements two key architectural patterns:

1. **MCP (Model Context Protocol) Servers** - Modular components that expose specific capabilities
2. **Agent Skills** - Reusable, self-contained components with clear interfaces

---

## MCP Server Architecture

### What is MCP?

Model Context Protocol (MCP) is a standard for connecting AI models to external tools and data sources. MCP servers provide:

- **Standardized interfaces** for tool access
- **Modular composition** of capabilities
- **Clear separation** of concerns
- **Reusable components** across projects

### MCP Servers in This Project

The project implements two MCP servers:

#### 1. YouTube MCP Server (`mcp_server_youtube.py`)

**Purpose**: Fetch and parse YouTube RSS feeds and transcripts

**MCP Pattern Implementation**:
```python
class YouTubeMCPServer:
    """YouTube MCP Server for RSS feed parsing and transcript extraction."""
    
    def __init__(self, timeout: int = 30):
        """Initialize YouTube MCP Server."""
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.rss_base_url = "https://www.youtube.com/feeds/videos.xml"
    
    def fetch_latest_videos_from_rss(self, channel_id: str) -> List[Dict[str, Any]]:
        """Fetch latest videos from YouTube channel RSS feed."""
        # Implementation...
    
    def get_video_transcript(self, video_id: str) -> Optional[str]:
        """Extract transcript from YouTube video."""
        # Implementation...
```

**MCP Features**:
- **Standardized Input**: Channel ID string
- **Standardized Output**: List of video dictionaries
- **Error Handling**: Graceful failure with logging
- **Timeout Management**: Configurable request timeouts
- **No State**: Stateless operation (can be instantiated multiple times)

#### 2. Telegram MCP Server (`mcp_server_notifier.py`)

**Purpose**: Send notifications via Telegram Bot API

**MCP Pattern Implementation**:
```python
class TelegramMCPServer:
    """Telegram Bot API MCP Server for sending notifications."""
    
    def __init__(self, bot_token: str, chat_id: str):
        """Initialize Telegram MCP Server."""
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, text: str, parse_mode: Optional[str] = "Markdown") -> bool:
        """Send text message to Telegram."""
        # Implementation...
    
    def send_document(self, document: str, caption: Optional[str] = None) -> bool:
        """Send document to Telegram."""
        # Implementation...
```

**MCP Features**:
- **Standardized Interface**: Message-based communication
- **Parameter Validation**: Input sanitization and limits
- **Error Responses**: Structured error handling
- **Rate Limiting**: Built-in message length limits
- **Retry Logic**: Exponential backoff for failures

### MCP Server Integration

The servers are integrated through the Agent Orchestrator:

```python
class AgentOrchestrator:
    """Background scheduler daemon for YouTube summarizer pipeline."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the orchestrator."""
        self.config = config or load_config()
        self.youtube_server = YouTubeMCPServer()  # MCP Server 1
        self.telegram_server = TelegramMCPServer(  # MCP Server 2
            self.config.telegram_bot_token,
            self.config.telegram_chat_id
        )
```

**Integration Pattern**:
- **Dependency Injection**: Config passed to servers
- **Loose Coupling**: Servers don't know about each other
- **Single Responsibility**: Each server handles one concern
- **Composable**: Servers can be swapped or extended

---

## Agent Skills Pattern

### What are Agent Skills?

Agent Skills are self-contained, reusable components that:

- **Perform specific tasks** (RSS parsing, notification sending)
- **Have clear interfaces** (input/output contracts)
- **Include documentation** (SKILL.md files)
- **Provide helper scripts** (ready-to-use utilities)
- **Are independently usable** (can be used in other projects)

### Agent Skills in This Project

#### 1. YouTube RSS Reader Skill

**Location**: `skills/youtube-rss-reader/`

**Structure**:
```
youtube-rss-reader/
├── SKILL.md              # Skill documentation
├── scripts/
│   └── find_channel_id.py  # Helper script
└── examples/
    └── basic_usage.py     # Usage examples
```

**SKILL.md Content**:
```markdown
---
name: youtube-rss-reader
description: Parse YouTube channel RSS feeds to discover new videos without API quotas.
---

# YouTube RSS Reader

## When to Use
- Monitoring YouTube channels for new videos
- Building RSS feed readers for YouTube content
- Extracting video metadata without API keys

## Process
1. Find Channel ID
2. Construct RSS Feed URL
3. Parse the Feed
4. Extract Video Information
```

**Helper Script** (`find_channel_id.py`):
```python
#!/usr/bin/env python3
"""
Convert YouTube channel handle to channel ID.

Usage:
    python find_channel_id.py @veritasium
    python find_channel_id.py @3blue1brown
"""
```

**Skill Features**:
- **Documentation-First**: Clear usage instructions
- **Self-Contained**: All dependencies documented
- **Reusable**: Can be used in other projects
- **Testable**: Includes example usage

#### 2. Telegram Notifier Skill

**Location**: `skills/telegram-notifier/`

**Structure**:
```
telegram-notifier/
├── SKILL.md              # Skill documentation
├── scripts/
│   └── send_message.py   # Helper script
└── examples/
    └── basic_usage.py    # Usage examples
```

**SKILL.md Content**:
```markdown
---
name: telegram-notifier
description: Send notifications via Telegram Bot API.
---

# Telegram Notifier

## When to Use
- Sending alerts and notifications
- Building monitoring systems
- Creating chatbots
- Delivering reports and summaries

## Process
1. Create Telegram Bot
2. Get Chat ID
3. Send Messages
```

**Helper Script** (`send_message.py`):
```python
#!/usr/bin/env python3
"""
Send a message via Telegram bot.

Usage:
    python send_message.py "Hello World"
    python send_message.py "Bold text" --parse-mode HTML
"""
```

**Skill Features**:
- **Complete Examples**: Ready-to-run scripts
- **Error Handling**: Robust error management
- **Formatting Support**: Markdown and HTML
- **Best Practices**: Documented guidelines

---

## MCP + Agent Skills Integration

### How They Work Together

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                         │
│  (Coordinates MCP servers and manages workflow)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ YouTube MCP     │    │ Telegram MCP    │                │
│  │ Server          │    │ Server          │                │
│  │ (mcp_server_    │    │ (mcp_server_    │                │
│  │  youtube.py)    │    │  notifier.py)   │                │
│  └────────┬────────┘    └────────┬────────┘                │
│           │                      │                          │
│           └──────────┬───────────┘                          │
│                      │                                      │
│  ┌───────────────────┴───────────────────┐                  │
│  │           Agent Skills                 │                  │
│  │  ┌─────────────┐  ┌─────────────┐    │                  │
│  │  │ YouTube RSS │  │ Telegram    │    │                  │
│  │  │ Reader      │  │ Notifier    │    │                  │
│  │  │ Skill       │  │ Skill       │    │                  │
│  │  └─────────────┘  └─────────────┘    │                  │
│  └───────────────────────────────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Orchestrator** calls YouTube MCP Server
2. **YouTube MCP Server** uses RSS feed parsing (from YouTube RSS Reader Skill)
3. **Orchestrator** processes data with Ollama
4. **Orchestrator** calls Telegram MCP Server
5. **Telegram MCP Server** sends formatted message (using Telegram Notifier Skill patterns)

---

## Benefits of This Architecture

### 1. Modularity

- **Separation of Concerns**: Each component has a single responsibility
- **Independent Development**: Components can be developed separately
- **Easy Testing**: Components can be tested in isolation

### 2. Reusability

- **Agent Skills**: Can be used in other projects
- **MCP Servers**: Can be instantiated multiple times
- **Helper Scripts**: Ready-to-use utilities

### 3. Maintainability

- **Clear Interfaces**: Easy to understand component boundaries
- **Documented**: SKILL.md files provide clear usage instructions
- **Extensible**: New skills can be added easily

### 4. Scalability

- **Horizontal Scaling**: Multiple MCP server instances
- **Vertical Scaling**: Individual components can be optimized
- **Load Distribution**: Work can be distributed across servers

---

## Example: Adding a New Agent Skill

### Step 1: Create Skill Directory

```
skills/
└── new-skill/
    ├── SKILL.md
    ├── scripts/
    │   └── helper.py
    └── examples/
        └── usage.py
```

### Step 2: Write SKILL.md

```markdown
---
name: new-skill
description: Description of what this skill does.
---

# New Skill

## When to Use
- Use case 1
- Use case 2

## Process
1. Step 1
2. Step 2
3. Step 3

## Helper Scripts
### helper.py
```bash
python skills/new-skill/scripts/helper.py [args]
```
```

### Step 3: Implement Helper Script

```python
#!/usr/bin/env python3
"""
Helper script for new skill.

Usage:
    python helper.py [arguments]
"""

def main():
    # Implementation
    pass

if __name__ == "__main__":
    main()
```

### Step 4: Add Examples

```python
#!/usr/bin/env python3
"""
Example usage of new skill.
"""

from new_skill import NewSkill

def main():
    skill = NewSkill()
    result = skill.do_something()
    print(f"Result: {result}")
```

---

## Comparison: MCP vs Agent Skills

| Aspect | MCP Servers | Agent Skills |
|--------|-------------|--------------|
| **Purpose** | Expose capabilities to AI models | Provide reusable components |
| **Interface** | Standardized API | Documentation + scripts |
| **State** | Can be stateful or stateless | Typically stateless |
| **Usage** | Called by orchestrator | Used by developers |
| **Documentation** | Inline code docs | SKILL.md files |
| **Examples** | Integration tests | Usage examples |

---

## Real-World Analogy

Think of this architecture like a **restaurant**:

- **Agent Orchestrator** = **Head Chef** (coordinates everything)
- **MCP Servers** = **Kitchen Stations** (specific tasks)
  - YouTube MCP = **Prep Station** (gathers ingredients)
  - Telegram MCP = **Plating Station** (presents the dish)
- **Agent Skills** = **Recipe Books** (reusable instructions)
  - YouTube RSS Skill = **Salad Recipe** (can be used anywhere)
  - Telegram Skill = **Dessert Recipe** (can be used anywhere)

---

## Conclusion

The YouTube Summarizer demonstrates:

1. **MCP Pattern**: Modular servers with standardized interfaces
2. **Agent Skills**: Reusable, documented components
3. **Clean Architecture**: Separation of concerns
4. **Extensibility**: Easy to add new capabilities
5. **Reusability**: Components can be used in other projects

This architecture makes the codebase:
- **Easier to maintain**
- **Easier to test**
- **Easier to extend**
- **Easier to understand**

---

*Last updated: 2026-06-21*
