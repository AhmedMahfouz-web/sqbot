# AI-Powered Internal Operations Assistant — Implementation Plan

## Overview
A Telegram bot that answers moderator questions about order issues using a Google Sheet as its knowledge base and Gemini 1.5 Flash as the AI engine. Deployed on Render free tier.

## Architecture

```
Moderator → Telegram Group → Telegram Bot API → Render Webhook → Bot (Python)
                                                                    │
                                                    ┌───────────────┴───────────────┐
                                                    ▼                               ▼
                                              Google Sheets                  Gemini 1.5 Flash
                                              (Knowledge Base)               (Answer Generation)
```

## Phases

### Phase 1: Setup (30 min)
1. Create Telegram bot via @BotFather — get `TELEGRAM_TOKEN`
2. Get Gemini API key from Google AI Studio
3. Create Google Cloud project, enable Sheets API, create service account, download JSON key
4. Share your order-issues sheet with the service account email
5. Create an "Unresolved" tab in the sheet (columns: Timestamp, Question)

### Phase 2: Code (already done — `bot.py`)
Single-file Python application using:
- `python-telegram-bot` — Telegram polling + health HTTP server for Render keep-alive
- `google-generativeai` — Gemini 1.5 Flash
- `gspread` — Google Sheets read/write
- Sheet data cached in memory for 5 min to avoid rate limits

### Phase 3: Deploy to Render (15 min)
1. Push code to GitHub/GitLab repo
2. Create new **Web Service** on Render, connect repo
3. **Runtime**: Python 3
4. **Build command**: `pip install -r requirements.txt`
5. **Start command**: `python bot.py`
6. Set environment variables (see `.env.example`) — paste `GOOGLE_CREDENTIALS` as a raw JSON string
7. Deploy — Render auto-installs deps and starts `bot.py`

### Phase 4: Keep-Alive (5 min)
Render free web services sleep after 15 min of inactivity — the bot uses polling (outbound traffic only), so the health endpoint keeps it alive.

Set up a free cron-job.org ping every 5 minutes:
- URL: `https://<your-app>.onrender.com/health`
- Interval: 5 minutes
- This counts as incoming traffic → Render stays awake

## Sheet Data Freshness
- Data fetched live from Sheets on every user message (no cache)
- Sheets API free tier (60 req/min) handles internal team volume easily
- If rate limits become an issue, a 60-second cache can be added back

## Escalation Flow
If Gemini can't find an answer (response contains "I cannot find an answer"), the bot appends the question to the "Unresolved" tab in the sheet, timestamped. Management reviews and updates the main sheet with the answer.

## Cost Breakdown
| Service        | Cost  |
|----------------|-------|
| Telegram Bot   | Free  |
| Gemini 1.5 Flash | Free (15 req/min) |
| Google Sheets API | Free |
| Render         | Free (web service, sleeps on idle) |
| cron-job.org   | Free  |
| **Total**      | **$0** |
