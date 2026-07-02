# Technical Specifications

## 1. System Overview
- **Name:** InternalOpsBot
- **Type:** Telegram group bot with AI-powered Q&A
- **Deployment:** Render web service (free tier)
- **Language:** Python 3.11+

## 2. Components

### 2.1 Telegram Interface
- Library: `python-telegram-bot` v21 (async)
- Mode: Polling (bot pulls updates from Telegram every few seconds)
- Keep-alive: Minimal HTTP server on `PORT` responds `200` to `/health` for Render keep-awake
- Scope: Restricted to a single group chat via `GROUP_ID`
- Commands:
  - `/start` — health check, returns confirmation

### 2.2 AI Engine
- Model: `gemini-1.5-flash` via `google-genai` SDK
- Context: Full sheet data injected into each prompt
- Fallback: If response contains "I cannot find an answer", escalation triggers

### 2.3 Google Sheets Integration
- Library: `gspread` with service account auth
- Main sheet: Read-only access, fetched live on every message (no cache)
- Unresolved sheet: Append-only log (Timestamp, Question)
- Auth: Service account JSON stored as Render secret file

## 3. Data Flow

```
User message → Telegram → bot.py (polling loop)
                                              │
                    ┌─────────────────────────┤
                    │                         │
                    ▼                         ▼
            Read sheet cache            Gemini API call
            (or refresh if stale)        (sheet data + question)
                    │                         │
                    └─────────────────────────┤
                                              │
                                    Can answer? ──Yes──→ Reply to group
                                              │
                                             No
                                              │
                                              ▼
                                  Append to Unresolved sheet
                                  Reply "No answer found"
```

## 4. Configuration

| Variable            | Source                          |
|---------------------|---------------------------------|
| TELEGRAM_TOKEN      | @BotFather                      |
| GEMINI_API_KEY      | Google AI Studio                |
| GROUP_ID            | Your Telegram group ID (int)    |
| SHEET_ID            | Google Sheet URL ID             |
| GOOGLE_CREDENTIALS  | GCP service account JSON (file) |
| PORT                | Set by Render (auto)            |

## 5. Security
- Bot only responds in the configured group — ignores DMs and other groups
- Service account has read access to the issue sheet, write access to Unresolved tab only
- No user authentication — relies on Telegram group membership
- No database — all state is in-memory

## 6. Limitations (Free Tier)
- Render sleeps after 15 min idle → use cron-job.org keep-alive
- Gemini free tier: 15 requests/min, 1,500 requests/day
- Single-process, no concurrency
- No conversation memory (stateless)
