import os
from typing import Any, Generator

# Set env vars before any app module is imported at collection time
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test-token")
os.environ.setdefault("SLACK_SIGNING_SECRET", "test-signing-secret-1234")
os.environ.setdefault("SLACK_BOT_USER_ID", "U0TEST123")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-api-key")

import pytest
from flask.testing import FlaskClient

from slack_bot.app import flask_app


@pytest.fixture
def flask_client() -> Generator[FlaskClient, Any, None]:
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client
