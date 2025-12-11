# EagleEye

AI-powered unified search Slack bot using Claude Agent SDK and MCP for Slack, Notion, Linear, and GitHub.

## Overview

EagleEye is a Slack bot that enables natural language search across your team's tools:
- **Slack**: Search messages and conversations
- **Notion**: Search pages and documents
- **Linear**: Search issues and projects
- **GitHub**: Search code, issues, and pull requests

Powered by Claude AI and the Model Context Protocol (MCP), EagleEye understands your questions and finds relevant information across all connected platforms.

## Features

- Natural language search across multiple platforms
- Real-time progress updates during search
- Query-based server filtering for faster responses
- Slack Block Kit formatted responses
- GitHub organization filtering support

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Slack Workspace                          │
│                    ┌─────────────┐                           │
│                    │ @EagleEye   │                           │
│                    └──────┬──────┘                           │
└───────────────────────────┼──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    EagleEye Bot (Python)                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Slack Bolt (Socket Mode)                │   │
│  └─────────────────────────┬───────────────────────────┘   │
│                            │                                 │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │           Claude Agent SDK + MCP Servers             │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │   │
│  │  │  Slack  │ │ Notion  │ │ Linear  │ │ GitHub  │   │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

- Python 3.12+
- Node.js 20+ (for MCP servers via npx)
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Claude CLI (`@anthropic-ai/claude-code`)
- Slack workspace with bot permissions

## Quick Start

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

### 3. Claude CLI authentication

```bash
npm install -g @anthropic-ai/claude-code
claude login
```

### 4. Run the bot

```bash
uv run python -m src

# With debug logging
DEBUG=true uv run python -m src
```

## Slack App Setup

1. Go to [Slack API](https://api.slack.com/apps) and create a new app
2. Enable **Socket Mode** and get the App-Level Token (`xapp-...`)
3. Add **Bot Token Scopes**:
   - `app_mentions:read`
   - `chat:write`
   - `channels:history`
   - `channels:read`
4. Install the app to your workspace and get the Bot Token (`xoxb-...`)

## API Keys

| Service | Where to get |
|---------|--------------|
| Slack Bot Token | Slack App > OAuth & Permissions |
| Slack App Token | Slack App > Basic Information > App-Level Tokens |
| Slack Team ID | Browser URL when logged into Slack |
| Notion API Key | [Notion Integrations](https://www.notion.so/my-integrations) |
| Linear API Key | [Linear Settings > API](https://linear.app/settings/api) |
| GitHub Token | [GitHub Settings > Tokens](https://github.com/settings/tokens) |

## Usage

Mention the bot in any channel:

```
@EagleEye 지난주 배포 관련 논의
@EagleEye authentication bug in Linear
@EagleEye ai-tutor 레포 최근 PR
```

EagleEye will search the relevant platforms and return formatted results with links.

## Configuration

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Slack bot OAuth token |
| `SLACK_APP_TOKEN` | Yes | Slack app-level token for Socket Mode |
| `SLACK_SIGNING_SECRET` | Yes | Slack app signing secret |
| `SLACK_TEAM_ID` | Yes | Slack workspace ID |
| `NOTION_API_KEY` | Yes | Notion integration API key |
| `LINEAR_API_KEY` | Yes | Linear API key |
| `GITHUB_TOKEN` | No | GitHub personal access token |
| `GITHUB_ORG` | No | Limit GitHub search to specific organization |
| `CLAUDE_MODEL` | No | Claude model (default: `claude-sonnet-4-20250514`) |
| `DEBUG` | No | Enable debug logging (default: `false`) |
| `ENABLE_SLACK_MCP` | No | Enable Slack search (default: `true`) |
| `ENABLE_NOTION_MCP` | No | Enable Notion search (default: `true`) |
| `ENABLE_LINEAR_MCP` | No | Enable Linear search (default: `true`) |
| `ENABLE_GITHUB_MCP` | No | Enable GitHub search (default: `true`) |

## Deployment

### Docker (Recommended)

```bash
# 1. Authenticate Claude CLI locally
claude login

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Build and run
docker compose up -d

# View logs
docker compose logs -f
```

### Manual Deployment

```bash
# Install dependencies
sudo yum install -y docker nodejs  # Amazon Linux
# or
sudo apt install -y docker.io nodejs  # Ubuntu

# Install Claude CLI
sudo npm install -g @anthropic-ai/claude-code
claude login

# Clone and configure
git clone <repo-url>
cd eagleeye
cp .env.example .env
# Edit .env

# Run with Docker
docker build -t eagleeye .
docker run -d \
  --name eagleeye \
  --restart unless-stopped \
  --env-file .env \
  -v ~/.claude:/root/.claude:ro \
  eagleeye
```

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
│   └── models/
│       └── search.py       # Search result models
├── tests/
│   ├── test_app.py
│   ├── test_claude_agent.py
│   ├── test_models.py
│   └── test_slack_formatter.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
└── README.md
```

## How it works

1. User mentions `@EagleEye` with a search query
2. EagleEye detects relevant platforms from the query keywords
3. Claude Agent SDK processes the query with filtered MCP servers
4. MCP servers search Slack, Notion, Linear, and GitHub
5. Claude synthesizes results into a Slack mrkdwn formatted response
6. Real-time progress updates are shown during the search
7. Final response is sent with Block Kit formatting and source links

## License

MIT
