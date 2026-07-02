# InternalOpsBot

A Telegram bot that answers moderator questions about order issues using a Google Sheet as its knowledge base and Gemini 1.5 Flash as the AI engine.

## How to run

The workflow `Start application` runs `python bot.py`. Start or restart it from the Replit workflow panel.

## Stack

- **Python 3.12**
- `python-telegram-bot` v21 — Telegram polling
- `google-genai` — Gemini 1.5 Flash
- `gspread` — Google Sheets read/write
- Minimal HTTP server on `PORT` (default 8080) for health checks

## Required secrets

Set all five in the Replit Secrets panel:

| Secret | Description |
|---|---|
| `TELEGRAM_TOKEN` | From @BotFather |
| `GEMINI_API_KEY` | From Google AI Studio |
| `GROUP_ID` | Telegram group numeric ID (e.g. `-1001234567890`) |
| `SHEET_ID` | ID from the Google Sheet URL — must be a **native** Google Sheet, not an Office/Excel file |
| `GOOGLE_CREDENTIALS` | Full GCP service account JSON (the `client_email` in this JSON must be shared as Editor on the sheet) |

## Architecture

- Bot polls Telegram for messages, restricted to the configured `GROUP_ID`
- On each message: fetches live sheet data, builds a prompt with sheet context + question, calls Gemini
- If Gemini can't answer, appends the question to an "Unresolved" tab in the sheet
- Health endpoint at `/` returns `200 ok` (used for keep-alive pings)

## User preferences

- Keep the single-file structure (`bot.py`) unless explicitly asked to change it
