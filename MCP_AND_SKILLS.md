# MCP Concepts and Agent Skills

This document explains how Model Context Protocol (MCP) concepts and Agent Skills are demonstrated and incorporated into the YouTube Summarizer program.

---

## Introduction: Understanding MCP, Agent Skills, and AI Agents

### What is an AI Agent?

Before we talk about MCP or Agent Skills, we need to understand what an **AI agent** actually is. Think about the difference between a calculator and a personal assistant. A calculator waits for you to type in numbers and press a button — it does exactly what you tell it, nothing more. A personal assistant, on the other hand, can understand what you want, figure out the steps needed to get there, and then do those steps on their own. They might make a phone call, send an email, check your calendar, and come back with an answer — all without you having to tell them each individual step.

An AI agent is like that personal assistant. Instead of just answering a question and stopping, an agent can *think*, *plan*, and *act*. It can break a big task into smaller steps, decide what tools it needs, use those tools, and then put the results together to accomplish something useful. For example, instead of just telling you what a YouTube video is about, an agent can check if a channel has posted new videos, download the transcripts, summarize them, and send you the summaries — all on its own, without you having to ask for each step.

This project uses an **Agent Orchestrator** — a central brain that coordinates everything. It decides when to check for new videos, calls the right tools to fetch and process them, and then calls other tools to deliver the results. The orchestrator is the personal assistant, and the MCP servers and Agent Skills are the tools it uses.

### What is MCP (Model Context Protocol)?

Now imagine you have a personal assistant who speaks English, but every tool in your office — the phone, the fax machine, the filing cabinet — speaks a different language. The phone speaks "phone language," the fax speaks "fax language," and the filing cabinet speaks "filing language." Your assistant would spend all day just trying to figure out how to talk to each tool, and would never actually get any work done.

This is the problem that **Model Context Protocol (MCP)** solves for AI. Before MCP, if a developer wanted an AI model to access a database, a file system, or a web service, they had to write a custom connection for each one. If they had ten different tools, they needed ten different custom connectors. If they added a second AI model, they needed ten more connectors — one for each combination of model and tool. This is called the "N×M problem," and it makes building AI systems incredibly complicated and expensive.

MCP, introduced by Anthropic in November 2024 and now supported by Google, OpenAI, Microsoft, and over 10,000 public servers, solves this by creating a single, standard language that all AI models and all tools can speak. Think of it like USB for your computer. Before USB, every device — printers, keyboards, mice, cameras — needed its own special port. USB gave everyone one universal port, and suddenly any device could plug into any computer. MCP does the same thing for AI: any model can plug into any tool, as long as both sides speak MCP.

In technical terms, MCP defines three roles. The **MCP Host** is the user-facing application — like Claude Desktop, or in our case, the Agent Orchestrator. The **MCP Client** lives inside the host and translates the AI's requests into MCP language. The **MCP Server** is the tool that provides data or capabilities — like our YouTube server that fetches video transcripts, or our Telegram server that sends messages. They communicate using a format called JSON-RPC 2.0, which is just a structured way of sending messages back and forth.

In this project, we implement two MCP servers. The YouTube MCP Server knows how to fetch RSS feeds and extract video transcripts. The Telegram MCP Server knows how to format and send messages. The Agent Orchestrator (our AI agent) talks to both of them using the MCP standard, and it could easily talk to any other MCP server in the future — for example, a server that reads email, or one that manages a calendar — without needing to write any new connection code.

### What are Agent Skills?

If MCP is the universal language that tools speak, then **Agent Skills** are the instruction manuals that tell the agent *how* to use those tools effectively. Think of Agent Skills like recipes in a cookbook. A recipe tells you exactly what ingredients you need, what steps to follow, and what the final dish should look like. You don't have to figure out from scratch how to make a cake — you just follow the recipe.

Agent Skills are self-contained packages of knowledge and code that perform a specific task. Each skill includes a `SKILL.md` file (the recipe), helper scripts (the kitchen tools), and examples (a picture of what the finished dish should look like). The beauty of Agent Skills is that they are *reusable* — once you write a skill for reading YouTube RSS feeds, you can use that same skill in any project, not just this one. You can also share your skills with other developers, who can drop them into their own projects.

In this project, we have two Agent Skills. The **YouTube RSS Reader Skill** contains everything needed to find a channel's ID, construct its RSS feed URL, parse the feed, and extract video information. The **Telegram Notifier Skill** contains everything needed to create a bot, get a chat ID, and send formatted messages. These skills are like specialized toolkits that the agent can pick up and use whenever it needs them.

### How the Kaggle 5-Day Course Shaped This Project

The Kaggle 5-Day AI Agents Intensive Course with Google taught thousands of learners how to build AI agents from the ground up. This project directly applies several key concepts from that course, particularly from Day 2 (Agent Tools & Interoperability), Day 3 (Context Engineering: Sessions, Skills & Memory), and Day 5 (Prototype to Production).

**From Day 2: Agent Tools & Interoperability.** The course teaches that powerful agents are not standalone — they connect to external tools, APIs, and other agents to extend their capabilities. The concept of "interoperability" means that tools should be able to work together seamlessly, regardless of who built them. This project implements that idea through MCP. Instead of building one monolithic program that does everything, we built two MCP servers that can interoperate with any MCP-compatible agent. The YouTube server and the Telegram server are like two specialized employees who each do their own job well and communicate through a standard protocol. The Agent Orchestrator coordinates them, but it could just as easily coordinate different servers — the architecture is designed to be flexible and interoperable.

**From Day 3: Context Engineering, Skills, and Memory.** The course explains that agents need to manage information efficiently. If an agent tries to load everything it knows into every conversation, it will run out of space and become slow — this is called "context rot." The solution is **Agent Skills**: portable directories of knowledge that an agent can load on demand, rather than all at once. This project implements Agent Skills exactly as the course describes. The `skills/youtube-rss-reader/` and `skills/telegram-notifier/` directories follow the same structure the course teaches: a central `SKILL.md` file with YAML frontmatter describing what the skill does, when to use it, and how to follow its process. The skills are self-contained, independently usable, and can be loaded by any agent that understands the format. This is the "progressive disclosure" pattern the course teaches — the agent only loads the knowledge it needs, when it needs it.

**From Day 5: Prototype to Production.** The course teaches that a working prototype is not the same as a production-ready system. To go from prototype to production, you need observability (logs that tell you what is happening), error handling (graceful failure when something goes wrong), and configurability (settings that can be adjusted without rewriting code). This project applies all three. The Agent Orchestrator logs every action it takes. The MCP servers handle errors gracefully and return structured responses. The entire system is configured through a `.env` file and an interactive setup wizard, so you can change channels, tokens, and schedules without touching the code. The course also teaches about "spec-driven development" — writing down what your system should do before you build it. This project follows that approach: each Agent Skill has a `SKILL.md` specification, each MCP server has a documented interface, and this document itself serves as the architectural specification.

### Why This Architecture Matters

The combination of MCP, Agent Skills, and the patterns taught in the Kaggle course creates a system that is greater than the sum of its parts. MCP gives us a universal language. Agent Skills give us reusable knowledge. The Agent Orchestrator gives us a brain that can think, plan, and act. And the production patterns from the course give us a system that is reliable, observable, and maintainable.

This architecture also makes the project *extensible*. Want to add support for a new video platform? Build a new MCP server and a new Agent Skill. Want to send summaries to email instead of Telegram? Build a new MCP server for email. Want to summarize podcast episodes instead of videos? Build a new MCP server for podcast feeds. Each new capability is just another building block that plugs into the same system, using the same universal language.

The sections that follow show exactly how each MCP server and Agent Skill is implemented, how they connect to the Agent Orchestrator, and how the data flows through the system to deliver your video summaries.

---

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
