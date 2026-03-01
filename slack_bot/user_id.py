import os
import ssl

import certifi
from custom_python_logger import build_logger, get_logger
from dotenv import find_dotenv, load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv(find_dotenv())

logger = get_logger(__name__)

ssl_context = ssl.create_default_context(cafile=certifi.where())


def get_bot_user_id() -> str | None:
    """Retrieve the bot's Slack user ID via the auth.test API.

    Returns:
        The bot's user ID string, or None if the API call fails.
    """
    try:
        slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"], ssl=ssl_context)
        response = slack_client.auth_test()
        return response["user_id"]
    except SlackApiError as e:
        logger.error("Failed to retrieve bot user ID: %s", e)
        return None


if __name__ == "__main__":
    build_logger(project_name="ticket-assist")
    logger.info("Bot user ID: %s", get_bot_user_id())
