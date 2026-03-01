![Python](https://img.shields.io/badge/python->=3.12-blue)
![Development Status](https://img.shields.io/badge/status-stable-green)
![Maintenance](https://img.shields.io/maintenance/yes/2026)
![License](https://img.shields.io/badge/license-MIT-blue)

---

# 💡 Python Slack Bot

A production-ready Slack bot built with **Slack Bolt** and **Flask**, designed for AI-powered customer support ticket classification. The bot listens for `app_mention` events, processes incoming messages, and is wired up for multi-LLM structured responses via Pydantic models.

---

## 📦 Installation

```bash
git clone https://github.com/aviz92/ticket-assist.git
cd ticket-assist
uv sync
```

---

## 🚀 Features

- ✅ **Slack Event Handling** — Responds to `app_mention` events in real time via Slack Bolt
- ✅ **Flask Webhook Server** — Exposes a `/slack/events` POST endpoint for Slack's Events API
- ✅ **AI-Ready Ticket Classification** — Pydantic schema (`TicketClassification`) with category, urgency, sentiment, confidence, and structured answer fields
- ✅ **Multi-LLM Support** — Pluggable LLM backend: Claude, Gemini, or OpenAI via `LLM_PROVIDER` env var
- ✅ **Structured Logging** — `custom-python-logger` with colored console output and configurable log levels
- ✅ **Code Quality** — Pre-commit hooks: Black, Ruff, Pylint (10.00/10), type hints throughout

---

## ⚙️ Configuration

Create a `.env` file in the project root with the following variables:

```env
# Slack App Credentials
SLACK_BOT_TOKEN=xoxb-your-bot-token        # starts with xoxb-
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_BOT_USER_ID=U0XXXXXXXXX             # run slack_bot/user_id.py to get this

# LLM Provider
LLM_PROVIDER=claude                        # Options: claude | gemini | openai
ANTHROPIC_API_KEY=your-anthropic-key
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
```

---

## 🛠️ Setup Guide

### Part 1 — Slack App Setup

#### 1. Create a new Slack app

- Go to [https://api.slack.com/apps](https://api.slack.com/apps) and sign in
- Click **"Create New App"** → choose a name and select your workspace → click **"Create App"**

#### 2. Set up your bot user

- Under **"Add features and functionality"**, click **"Bots"**
- Click **"Add a Bot User"**, fill in the display name and username, and save

#### 3. Add bot token scopes

- In the left sidebar, click **"OAuth & Permissions"**
- Scroll to **"Scopes"** → **"Bot Token Scopes"** and add:
  - `app_mentions:read`
  - `chat:write`
  - `channels:history`

#### 4. Install the bot to your workspace

- In the left sidebar, click **"Install App"**
- Click **"Install App to Workspace"** and authorize

#### 5. Retrieve your credentials

- After installation, go to **"OAuth & Permissions"** and copy the **Bot User OAuth Token** (starts with `xoxb-`)
- Go to **"Basic Information"** → **"App Credentials"** and copy the **Signing Secret**
- Run `uv run python slack_bot/user_id.py` to print your **Bot User ID**

---

### Part 2 — Python Setup

#### 1. Install SSL certificates (macOS only)

Required for Python to validate Slack's TLS certificates:

```bash
# Python < 3.13
/Applications/Python\ 3.x/Install\ Certificates.command

# Python 3.13+
/Applications/Python\ 3.13/Install\ Certificates.command
```

#### 2. Configure your `.env` file

Fill in the credentials from Part 1 into your `.env` file (see [Configuration](#️-configuration) above).

#### 3. Start the Flask server

```bash
uv run python -m slack_bot.app
```

The server starts on [http://127.0.0.1:5000](http://127.0.0.1:5000). You should see log output confirming it's running.

> **Note:** If port 5000 is already in use, stop the conflicting process or run on a different port:
> `uv run python -m slack_bot.app --port 8080`

---

### Part 3 — Expose the Server with ngrok

#### 1. Install and start ngrok

```bash
# macOS via Homebrew
brew install ngrok

# Start tunnel on port 5000
ngrok http 5000
```

Note the HTTPS URL provided (e.g. `https://yoursubdomain.ngrok.io`).

> **Important:** Every time you restart ngrok, you get a **new URL** — you must update it in Slack each time (for testing only).

#### 2. Configure Slack Event Subscriptions

- Go to [https://api.slack.com/apps](https://api.slack.com/apps) → your app → **"Event Subscriptions"**
- Enable events and set the **Request URL** to:
  ```
  https://yoursubdomain.ngrok.io/slack/events
  ```
- Slack will verify the URL — your Flask server must be running for this to succeed
- Scroll to **"Subscribe to bot events"** → **"Add Bot User Event"** → add `app_mention` → save

#### 3. Reinstall the app to apply permission changes

- Go to **"Install App"** → click **"Reinstall App to Workspace"** and authorize

#### 4. Invite the bot to a channel

In any Slack channel, type:

```
/invite @YourBotName
```

The bot will now respond to `@YourBotName <message>` mentions in that channel.

---

### Part 4 — Add Custom Functions

To replace the demo `my_function` with your own AI logic, edit `handle_mentions` in `slack_bot/app.py`:

```python
@app.event("app_mention")
def handle_mentions(body: dict[str, Any], say: Say) -> None:
    text = body["event"]["text"]
    mention = f"<@{SLACK_BOT_USER_ID}>"
    text = text.replace(mention, "").strip()

    say("thinking...")
    response = ai_function(llm=llm, user_input=text)  # your function here
    say(response.answer)
```

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Install SSL certificates (macOS)
/Applications/Python\ 3.13/Install\ Certificates.command

# 3. Configure environment
cp .env.example .env   # fill in your Slack credentials

# 4. Get your bot user ID
uv run python slack_bot/user_id.py

# 5. Start the Flask server
uv run python -m slack_bot.app

# 6. In a new terminal, start ngrok
ngrok http 5000
```

Then set `https://<your-ngrok-url>/slack/events` as your Slack app's Event Subscriptions URL and invite the bot to a channel with `/invite @YourBotName`.

---

## ▶️ Usage Examples

### Example 1: Handling a bot mention

When a user mentions the bot in Slack, `handle_mentions` strips the mention tag, processes the text, and replies:

```python
# slack_bot/app.py
@app.event("app_mention")
def handle_mentions(body: dict[str, Any], say: Say) -> None:
    text = body["event"]["text"]
    mention = f"<@{SLACK_BOT_USER_ID}>"
    text = text.replace(mention, "").strip()

    say("thinking...")
    response = my_function(text)  # replace with your AI call
    say(response)
```

### Example 2: AI ticket classification schema

Use `TicketClassification` as the `response_model` for structured LLM output:

```python
from slack_bot.functions import TicketClassification, SYSTEM_PROMPT

# With your LLM client (instructor-style):
response = llm.completions_create(
    response_model=TicketClassification,
    temperature=0,
    max_retries=3,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "My order #12345 hasn't arrived yet"},
    ],
)

print(response.category)        # TicketCategory.ORDER_ISSUE
print(response.urgency)         # TicketUrgency.HIGH
print(response.ticket_complete) # True / False
print(response.answer)          # Ready-to-send customer reply
```

### Example 3: Fetching the bot's user ID

```python
from slack_bot.user_id import get_bot_user_id

bot_id = get_bot_user_id()
print(f"Bot user ID: {bot_id}")  # e.g. U0XXXXXXXXX
```

---

## 🤝 Contributing

If you have a helpful pattern or improvement to suggest:

1. Fork the repo
2. Create a new branch
3. Submit a pull request

Contributions that improve AI integration, error handling, or test coverage are especially welcome.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Thanks

Thanks for exploring this repository!
Happy coding!
