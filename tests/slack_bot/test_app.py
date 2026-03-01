from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient

import slack_bot.app as app_module
from slack_bot.app import _process_and_reply, conversation_store, handle_mentions, handle_message


@pytest.fixture(autouse=True)
def clear_conversation_store() -> Any:
    conversation_store.clear()
    yield
    conversation_store.clear()


def _make_complete_ticket() -> MagicMock:
    ticket = MagicMock()
    ticket.ticket_complete = True
    ticket.answer = "Your issue is resolved."
    ticket.category.value = "order_issue"
    ticket.urgency.value = "high"
    ticket.sentiment.value = "frustrated"
    ticket.confidence = 0.95
    ticket.key_information = ["order #999"]
    ticket.suggested_action = "Check shipping"
    return ticket


def _mention(user_id: str) -> str:
    """Build a Slack mention tag for the given user ID."""
    return f"<@{user_id}>"


class TestHealthEndpoint:
    def test_returns_200(self, flask_client: FlaskClient) -> None:
        response = flask_client.get("/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_returns_ok_body(self, flask_client: FlaskClient) -> None:
        response = flask_client.get("/health")
        assert response.data == b"OK", f"Expected b'OK', got {response.data}"


class TestProcessAndReply:
    def test_says_thinking_first(self) -> None:
        conversation_store["C123"] = [{"role": "user", "content": "help"}]
        mock_say = MagicMock()

        with patch("slack_bot.app.ai_function", return_value=_make_complete_ticket()):
            _process_and_reply("C123", mock_say)

        assert mock_say.call_args_list[0][0][0] == "thinking...", "First say call should be 'thinking...'"

    def test_complete_ticket_clears_conversation(self) -> None:
        conversation_store["C123"] = [{"role": "user", "content": "help"}]

        with patch("slack_bot.app.ai_function", return_value=_make_complete_ticket()):
            _process_and_reply("C123", MagicMock())

        assert "C123" not in conversation_store, "Completed ticket should remove channel from store"

    def test_complete_ticket_sends_summary(self) -> None:
        conversation_store["C123"] = [{"role": "user", "content": "help"}]
        mock_say = MagicMock()

        with patch("slack_bot.app.ai_function", return_value=_make_complete_ticket()):
            _process_and_reply("C123", mock_say)

        summary = mock_say.call_args_list[1][0][0]
        assert "order_issue" in summary, "Summary should contain category"
        assert "high" in summary, "Summary should contain urgency"

    def test_incomplete_ticket_keeps_conversation_open(self) -> None:
        conversation_store["C123"] = [{"role": "user", "content": "help"}]
        mock_ticket = MagicMock()
        mock_ticket.ticket_complete = False
        mock_ticket.answer = "Can you clarify?"

        with patch("slack_bot.app.ai_function", return_value=mock_ticket):
            _process_and_reply("C123", MagicMock())

        assert "C123" in conversation_store, "Incomplete ticket should keep conversation open"

    def test_incomplete_ticket_appends_assistant_message(self) -> None:
        conversation_store["C123"] = [{"role": "user", "content": "help"}]
        mock_ticket = MagicMock()
        mock_ticket.ticket_complete = False
        mock_ticket.answer = "Can you clarify?"

        with patch("slack_bot.app.ai_function", return_value=mock_ticket):
            _process_and_reply("C123", MagicMock())

        last_msg = conversation_store["C123"][-1]
        assert last_msg == {"role": "assistant", "content": "Can you clarify?"}, "Assistant reply should be appended"

    def test_incomplete_ticket_says_answer(self) -> None:
        conversation_store["C123"] = [{"role": "user", "content": "help"}]
        mock_say = MagicMock()
        mock_ticket = MagicMock()
        mock_ticket.ticket_complete = False
        mock_ticket.answer = "Which item is affected?"

        with patch("slack_bot.app.ai_function", return_value=mock_ticket):
            _process_and_reply("C123", mock_say)

        assert mock_say.call_args_list[1][0][0] == "Which item is affected?", "Should say the answer for incomplete ticket"


class TestHandleMentions:
    def test_empty_text_sends_greeting(self) -> None:
        mock_say = MagicMock()
        # Use the actual SLACK_BOT_USER_ID the module loaded so the mention is stripped correctly
        bot_uid = app_module.SLACK_BOT_USER_ID
        body: dict[str, Any] = {"event": {"channel": "C123", "text": _mention(bot_uid)}}

        handle_mentions(body=body, say=mock_say)

        mock_say.assert_called_once_with("Hi! Please describe your issue and I'll help open a support ticket.")

    def test_valid_text_stores_user_message(self) -> None:
        mock_say = MagicMock()
        bot_uid = app_module.SLACK_BOT_USER_ID
        body: dict[str, Any] = {"event": {"channel": "C456", "text": f"{_mention(bot_uid)} my order is late"}}
        mock_ticket = MagicMock()
        mock_ticket.ticket_complete = False
        mock_ticket.answer = "I can help."

        with patch("slack_bot.app.ai_function", return_value=mock_ticket):
            handle_mentions(body=body, say=mock_say)

        assert "C456" in conversation_store, "Channel should be added to conversation_store"
        assert conversation_store["C456"][0] == {"role": "user", "content": "my order is late"}

    def test_mention_tag_and_whitespace_stripped(self) -> None:
        mock_say = MagicMock()
        bot_uid = app_module.SLACK_BOT_USER_ID
        body: dict[str, Any] = {"event": {"channel": "C789", "text": f"{_mention(bot_uid)}   billing question  "}}
        mock_ticket = MagicMock()
        mock_ticket.ticket_complete = False
        mock_ticket.answer = "Sure."

        with patch("slack_bot.app.ai_function", return_value=mock_ticket):
            handle_mentions(body=body, say=mock_say)

        assert conversation_store["C789"][0]["content"] == "billing question", "Mention and surrounding whitespace should be stripped"


class TestHandleMessage:
    def test_bot_message_is_ignored(self) -> None:
        mock_say = MagicMock()
        body: dict[str, Any] = {"event": {"channel": "C123", "text": "bot reply", "bot_id": "B123"}}

        handle_message(body=body, say=mock_say)

        mock_say.assert_not_called()

    def test_subtype_message_is_ignored(self) -> None:
        mock_say = MagicMock()
        body: dict[str, Any] = {"event": {"channel": "C123", "text": "edited", "subtype": "message_changed"}}

        handle_message(body=body, say=mock_say)

        mock_say.assert_not_called()

    def test_empty_text_is_ignored(self) -> None:
        conversation_store["C123"] = [{"role": "user", "content": "help"}]
        mock_say = MagicMock()
        body: dict[str, Any] = {"event": {"channel": "C123", "text": ""}}

        handle_message(body=body, say=mock_say)

        mock_say.assert_not_called()

    @pytest.mark.parametrize("reset_command", ["start-over", "restart", "reset"])
    def test_reset_command_clears_conversation(self, reset_command: str) -> None:
        conversation_store["C123"] = [{"role": "user", "content": "help"}]
        mock_say = MagicMock()
        body: dict[str, Any] = {"event": {"channel": "C123", "text": reset_command}}

        handle_message(body=body, say=mock_say)

        assert "C123" not in conversation_store, f"Reset command '{reset_command}' should clear conversation"
        mock_say.assert_called_once_with("Conversation reset. Mention me to start a new ticket.")

    def test_message_without_active_conversation_is_ignored(self) -> None:
        mock_say = MagicMock()
        body: dict[str, Any] = {"event": {"channel": "C_UNKNOWN", "text": "hello"}}

        handle_message(body=body, say=mock_say)

        mock_say.assert_not_called()

    def test_message_appended_to_active_conversation(self) -> None:
        conversation_store["C123"] = [{"role": "user", "content": "first message"}]
        mock_say = MagicMock()
        body: dict[str, Any] = {"event": {"channel": "C123", "text": "follow up"}}
        mock_ticket = MagicMock()
        mock_ticket.ticket_complete = False
        mock_ticket.answer = "Got it."

        with patch("slack_bot.app.ai_function", return_value=mock_ticket):
            handle_message(body=body, say=mock_say)

        user_messages = [m for m in conversation_store["C123"] if m["role"] == "user"]
        assert any(m["content"] == "follow up" for m in user_messages), "Follow-up message should be appended to store"
