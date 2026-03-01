import os
import ssl
from typing import Any

import certifi
from custom_python_logger import build_logger
from dotenv import load_dotenv
from flask import Flask, Response, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt.context.say import Say

from slack_bot.functions import ai_function

load_dotenv()

logger = build_logger(project_name="ticket-assist")

ssl_context = ssl.create_default_context(cafile=certifi.where())

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
SLACK_BOT_USER_ID = os.environ["SLACK_BOT_USER_ID"]

logger.info("Using signing secret: %s...%s", SLACK_SIGNING_SECRET[:4], SLACK_SIGNING_SECRET[-4:])

app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

# keyed by channel_id → list of {"role": "user"/"assistant", "content": str}
conversation_store: dict[str, list[dict[str, str]]] = {}

RESET_COMMANDS = {"start-over", "restart", "reset"}


def _process_and_reply(channel: str, say: Say) -> None:
    say("thinking...")
    result = ai_function(conversation_store[channel])

    conversation_store[channel].append({"role": "assistant", "content": result.answer})

    if result.ticket_complete:
        summary = (
            f"{result.answer}\n\n"
            f"*Summary*\n"
            f"• Category: {result.category.value}\n"
            f"• Urgency: {result.urgency.value}\n"
            f"• Sentiment: {result.sentiment.value}\n"
            f"• Confidence: {result.confidence:.0%}\n"
            f"• Key info: {', '.join(result.key_information)}\n"
            f"• Suggested action: {result.suggested_action}"
        )
        say(summary)
        conversation_store.pop(channel, None)
    else:
        say(result.answer)


@app.event("app_mention")
def handle_mentions(body: dict[str, Any], say: Say) -> None:
    channel = body["event"]["channel"]
    text = body["event"]["text"]
    mention = f"<@{SLACK_BOT_USER_ID}>"
    text = text.replace(mention, "").strip()

    if not text:
        say("Hi! Please describe your issue and I'll help open a support ticket.")
        return

    conversation_store[channel] = [{"role": "user", "content": text}]
    _process_and_reply(channel, say)


@app.event("message")
def handle_message(body: dict[str, Any], say: Say) -> None:
    event = body["event"]

    if event.get("bot_id") or event.get("subtype"):
        return

    channel = event["channel"]
    text = event.get("text", "").strip()

    if not text:
        return

    if text.lower() in RESET_COMMANDS:
        conversation_store.pop(channel, None)
        say("Conversation reset. Mention me to start a new ticket.")
        return

    if channel not in conversation_store:
        return

    conversation_store[channel].append({"role": "user", "content": text})
    _process_and_reply(channel, say)


@flask_app.route("/health", methods=["GET"])
def health() -> Response:
    """Health check endpoint."""
    return Response("OK", status=200)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events() -> Response:
    """Route for handling Slack events.

    Returns:
        The result of handling the incoming Slack request.
    """
    return handler.handle(request)


if __name__ == "__main__":
    flask_app.run(host="127.0.0.1")
