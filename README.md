# EagleEye

AI-powered unified search Slack bot using Claude and MCP for Slack, Notion, and Linear.

## Overview

EagleEye is a Slack bot that enables natural language search across your team's tools:
- **Slack**: Search messages and conversations
- **Notion**: Search pages and documents
- **Linear**: Search issues and projects

Powered by Claude AI and the Model Context Protocol (MCP), EagleEye understands your questions and finds relevant information across all connected platforms.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Slack Workspace                          │
│  ┌─────────────┐  ┌─────────────┐                           │
│  │ /search cmd │  │ @EagleEye   │                           │
│  └──────┬──────┘  └──────┬──────┘                           │
└─────────┼────────────────┼──────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                    EagleEye Bot (Python)                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Slack Bolt (Socket Mode)                │   │
│  └─────────────────────────┬───────────────────────────┘   │
│                            │                                 │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │           Claude Agent SDK + MCP Servers             │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐       │   │
│  │  │ Slack MCP │  │ Notion MCP│  │ Linear MCP│       │   │
│  │  └───────────┘  └───────────┘  └───────────┘       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Node.js 18+ (for MCP servers)
- Slack workspace with bot permissions

## Installation

### 1. Clone and setup

```bash
git clone https://github.com/your-org/eagleeye.git
cd eagleeye

# Using uv (recommended)
uv sync

# Or using pip
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Slack App Setup

1. Go to [Slack API](https://api.slack.com/apps) and create a new app
2. Enable **Socket Mode** and get the App-Level Token (`xapp-...`)
3. Add **Bot Token Scopes**:
   - `app_mentions:read`
   - `chat:write`
   - `channels:history`
   - `channels:read`
   - `commands`
4. Install the app to your workspace and get the Bot Token (`xoxb-...`)
5. Create a slash command `/search`

### 4. API Keys

| Service | Where to get |
|---------|--------------|
| Slack Bot Token | Slack App > OAuth & Permissions |
| Slack App Token | Slack App > Basic Information > App-Level Tokens |
| Slack Team ID | Browser URL when logged into Slack |
| Notion API Key | [Notion Integrations](https://www.notion.so/my-integrations) |
| Linear API Key | [Linear Settings > API](https://linear.app/settings/api) |

## Usage

### Start the bot

```bash
# Using uv
uv run python -m src

# With debug logging
DEBUG=true uv run python -m src
```

### Search commands

**Slash command:**
```
/search 지난주 배포 관련 논의
/search authentication bug in Linear
/search project documentation
```

**Mention:**
```
@EagleEye 인증 버그 이슈 찾아줘
@EagleEye where is the API documentation?
```

## Configuration

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Slack bot OAuth token |
| `SLACK_APP_TOKEN` | Yes | Slack app-level token for Socket Mode |
| `SLACK_SIGNING_SECRET` | Yes | Slack app signing secret |
| `SLACK_TEAM_ID` | Yes | Slack workspace ID |
| `NOTION_API_KEY` | Yes | Notion integration API key |
| `LINEAR_API_KEY` | Yes | Linear API key |
| `CLAUDE_MODEL` | No | Claude model (default: `claude-sonnet-4-20250514`) |
| `DEBUG` | No | Enable debug logging (default: `false`) |
| `ENABLE_SLACK_MCP` | No | Enable Slack search (default: `true`) |
| `ENABLE_NOTION_MCP` | No | Enable Notion search (default: `true`) |
| `ENABLE_LINEAR_MCP` | No | Enable Linear search (default: `true`) |

## Development

### Run tests

```bash
uv run pytest tests/ -v
```

### Code quality

```bash
# Linting
uv run ruff check src/ tests/

# Type checking
uv run mypy src/

# Format
uv run ruff format src/ tests/
```

### Project structure

```
eagleeye/
├── src/
│   ├── __main__.py         # Entry point
│   ├── app.py              # Slack bot application
│   ├── claude_agent.py     # Claude Agent SDK integration
│   ├── config.py           # Settings management
│   ├── log_config.py       # Structured logging
│   ├── slack_formatter.py  # Slack Block Kit formatting
│   ├── models/
│   │   └── search.py       # Search result models
│   └── mcp_integration/
│       ├── client.py       # MCP client wrapper
│       └── servers.py      # MCP server configurations
├── tests/
│   ├── conftest.py         # Test fixtures
│   ├── test_app.py         # Bot tests
│   ├── test_mcp.py         # MCP integration tests
│   ├── test_models.py      # Model tests
│   └── test_slack_formatter.py
├── pyproject.toml
├── .env.example
└── README.md
```

## How it works

1. User sends a search query via `/search` or `@EagleEye`
2. EagleEye uses Claude Agent SDK to understand the query
3. Claude decides which MCP tools to use based on the query
4. MCP servers search Slack, Notion, and Linear
5. Claude synthesizes results into a formatted Slack response
6. Response is sent back with Block Kit formatting

## License

MIT
