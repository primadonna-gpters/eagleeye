"""Entry point for running EagleEye bot."""

import os

from eagleeye.app import EagleEyeBot
from eagleeye.config import get_settings
from eagleeye.logging import configure_logging


def main() -> None:
    """Run the EagleEye bot."""
    # Use JSON format in production (when ENVIRONMENT=production)
    json_format = os.getenv("ENVIRONMENT", "development") == "production"
    configure_logging(json_format=json_format)

    settings = get_settings()
    bot = EagleEyeBot(settings)
    bot.start()


if __name__ == "__main__":
    main()
