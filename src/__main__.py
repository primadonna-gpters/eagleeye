"""Entry point for running EagleEye bot."""

import os
import sys

# Debug: print environment variables (remove after testing)
print("=== DEBUG: Environment Variables ===", file=sys.stderr)
for key in ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "SLACK_SIGNING_SECRET",
            "SLACK_TEAM_ID", "NOTION_API_KEY", "LINEAR_API_KEY"]:
    value = os.environ.get(key, "NOT SET")
    masked = value[:4] + "..." if value != "NOT SET" and len(value) > 4 else value
    print(f"{key}: {masked}", file=sys.stderr)
print("===================================", file=sys.stderr)

from app import EagleEyeBot
from config import get_settings
from log_config import configure_logging


def main() -> None:
    """Run the EagleEye bot."""
    settings = get_settings()

    # Use JSON format in production (when ENVIRONMENT=production)
    json_format = os.getenv("ENVIRONMENT", "development") == "production"
    configure_logging(json_format=json_format, debug=settings.debug)

    bot = EagleEyeBot(settings)
    bot.start()


if __name__ == "__main__":
    main()
