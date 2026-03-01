from unittest.mock import MagicMock, patch

from slack_sdk.errors import SlackApiError

from slack_bot.user_id import get_bot_user_id


class TestGetBotUserId:
    def test_returns_user_id_on_success(self) -> None:
        with patch("slack_bot.user_id.WebClient") as mock_web_client_cls:
            mock_client = MagicMock()
            mock_client.auth_test.return_value = {"user_id": "U0ABC123"}
            mock_web_client_cls.return_value = mock_client

            result = get_bot_user_id()

        assert result == "U0ABC123", f"Expected 'U0ABC123', got {result}"

    def test_returns_none_on_slack_api_error(self) -> None:
        with patch("slack_bot.user_id.WebClient") as mock_web_client_cls:
            mock_client = MagicMock()
            mock_client.auth_test.side_effect = SlackApiError("invalid_auth", MagicMock())
            mock_web_client_cls.return_value = mock_client

            result = get_bot_user_id()

        assert result is None, f"Expected None on SlackApiError, got {result}"

    def test_calls_auth_test(self) -> None:
        with patch("slack_bot.user_id.WebClient") as mock_web_client_cls:
            mock_client = MagicMock()
            mock_client.auth_test.return_value = {"user_id": "U0XYZ"}
            mock_web_client_cls.return_value = mock_client

            get_bot_user_id()

            mock_client.auth_test.assert_called_once()
