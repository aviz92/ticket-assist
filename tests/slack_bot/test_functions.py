from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from slack_bot.functions import (
    SYSTEM_PROMPT,
    CustomerSentiment,
    TicketCategory,
    TicketClassification,
    TicketUrgency,
    ai_function,
)


class TestTicketCategory:
    def test_values_are_correct(self) -> None:
        assert TicketCategory.ORDER_ISSUE.value == "order_issue"
        assert TicketCategory.ACCOUNT_ACCESS.value == "account_access"
        assert TicketCategory.PRODUCT_INQUIRY.value == "product_inquiry"
        assert TicketCategory.TECHNICAL_SUPPORT.value == "technical_support"
        assert TicketCategory.BILLING.value == "billing"
        assert TicketCategory.OTHER.value == "other"

    def test_is_string_enum(self) -> None:
        assert isinstance(TicketCategory.ORDER_ISSUE, str), "TicketCategory should be a str enum"


class TestCustomerSentiment:
    def test_values_are_correct(self) -> None:
        assert CustomerSentiment.ANGRY.value == "angry"
        assert CustomerSentiment.FRUSTRATED.value == "frustrated"
        assert CustomerSentiment.NEUTRAL.value == "neutral"
        assert CustomerSentiment.SATISFIED.value == "satisfied"


class TestTicketUrgency:
    def test_values_are_correct(self) -> None:
        assert TicketUrgency.LOW.value == "low"
        assert TicketUrgency.MEDIUM.value == "medium"
        assert TicketUrgency.HIGH.value == "high"
        assert TicketUrgency.CRITICAL.value == "critical"


class TestTicketClassification:
    def _valid_payload(self) -> dict:
        return {
            "category": TicketCategory.ORDER_ISSUE,
            "urgency": TicketUrgency.HIGH,
            "sentiment": CustomerSentiment.FRUSTRATED,
            "confidence": 0.9,
            "key_information": ["order #12345", "not delivered"],
            "suggested_action": "Check shipping status",
            "answer": "We are looking into your order.",
            "ticket_complete": True,
        }

    def test_valid_creation(self) -> None:
        ticket = TicketClassification(**self._valid_payload())
        assert ticket.category == TicketCategory.ORDER_ISSUE, "Category should match"
        assert ticket.urgency == TicketUrgency.HIGH, "Urgency should match"
        assert ticket.sentiment == CustomerSentiment.FRUSTRATED, "Sentiment should match"
        assert ticket.confidence == 0.9, "Confidence should match"
        assert ticket.ticket_complete is True, "ticket_complete should be True"

    def test_confidence_boundary_zero(self) -> None:
        payload = self._valid_payload()
        payload["confidence"] = 0.0
        ticket = TicketClassification(**payload)
        assert ticket.confidence == 0.0, "Confidence of 0.0 should be valid"

    def test_confidence_boundary_one(self) -> None:
        payload = self._valid_payload()
        payload["confidence"] = 1.0
        ticket = TicketClassification(**payload)
        assert ticket.confidence == 1.0, "Confidence of 1.0 should be valid"

    def test_confidence_below_zero_raises_validation_error(self) -> None:
        payload = self._valid_payload()
        payload["confidence"] = -0.1
        with pytest.raises(ValidationError):
            TicketClassification(**payload)

    def test_confidence_above_one_raises_validation_error(self) -> None:
        payload = self._valid_payload()
        payload["confidence"] = 1.1
        with pytest.raises(ValidationError):
            TicketClassification(**payload)

    def test_key_information_is_list(self) -> None:
        ticket = TicketClassification(**self._valid_payload())
        assert isinstance(ticket.key_information, list), "key_information should be a list"

    def test_ticket_incomplete_flag(self) -> None:
        payload = self._valid_payload()
        payload["ticket_complete"] = False
        ticket = TicketClassification(**payload)
        assert ticket.ticket_complete is False, "ticket_complete should be False"


class TestSystemPrompt:
    def test_is_non_empty_string(self) -> None:
        assert isinstance(SYSTEM_PROMPT, str), "SYSTEM_PROMPT should be a string"
        assert len(SYSTEM_PROMPT) > 0, "SYSTEM_PROMPT should not be empty"

    def test_contains_key_instructions(self) -> None:
        assert "ticket_complete" in SYSTEM_PROMPT, "SYSTEM_PROMPT should mention ticket_complete"
        assert "confidence" in SYSTEM_PROMPT, "SYSTEM_PROMPT should mention confidence"


class TestAiFunction:
    def test_returns_ticket_classification(self) -> None:
        mock_result = MagicMock(spec=TicketClassification)
        messages = [{"role": "user", "content": "My order hasn't arrived"}]

        # Patch anthropic.Anthropic to avoid SSL cert lookup, then patch instructor
        with patch("slack_bot.functions.anthropic.Anthropic") as mock_anthropic_cls:
            with patch("slack_bot.functions.instructor.from_anthropic") as mock_from_anthropic:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_result
                mock_from_anthropic.return_value = mock_client

                result = ai_function(messages)

        assert result is mock_result, "ai_function should return the LLM result"
        mock_client.chat.completions.create.assert_called_once()
        mock_anthropic_cls.assert_called_once()

    def test_passes_messages_and_response_model(self) -> None:
        mock_result = MagicMock(spec=TicketClassification)
        messages = [{"role": "user", "content": "Billing issue"}]

        with patch("slack_bot.functions.anthropic.Anthropic"):
            with patch("slack_bot.functions.instructor.from_anthropic") as mock_from_anthropic:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_result
                mock_from_anthropic.return_value = mock_client

                ai_function(messages)

                call_kwargs = mock_client.chat.completions.create.call_args.kwargs
                assert call_kwargs["messages"] == messages, "Messages should be passed to the LLM"
                assert call_kwargs["response_model"] is TicketClassification, "response_model should be TicketClassification"
