# EagleEye - AI-powered unified search Slack bot
FROM python:3.12-slim

# Install Node.js (required for MCP servers via npx)
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN pip install uv

# Install Claude CLI
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Pre-cache MCP server packages (optional, speeds up first run)
RUN npx -y @modelcontextprotocol/server-slack --version || true
RUN npx -y @notionhq/notion-mcp-server --version || true
RUN npx -y @tacticlaunch/mcp-linear --version || true
RUN npx -y @modelcontextprotocol/server-github --version || true

# Create non-root user (required for Claude CLI)
RUN useradd -m -u 1000 eagleuser
RUN chown -R eagleuser:eagleuser /app

# Environment variables (override at runtime)
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV PYTHONPATH=/app/src

# Switch to non-root user
USER eagleuser

# Run the bot
WORKDIR /app
CMD ["uv", "run", "python", "/app/src/__main__.py"]
