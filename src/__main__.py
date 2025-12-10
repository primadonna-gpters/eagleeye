"""Entry point for running EagleEye bot."""

import os

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
