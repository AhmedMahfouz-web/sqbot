import asyncio
import os
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GROUP_ID = int(os.environ["GROUP_ID"])
SHEET_ID = os.environ["SHEET_ID"]
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

client = genai.Client(api_key=GEMINI_API_KEY)

try:
    gc = gspread.service_account_from_dict(json.loads(os.environ["GOOGLE_CREDENTIALS"]))
    sheet = gc.open_by_key(SHEET_ID)
except APIError as e:
    err_text = str(e)
    if "must not be an Office file" in err_text or "not supported for this document" in err_text:
        logging.error(
            "\n"
            "========================================================================\n"
            "CONFIG ERROR: The SHEET_ID environment variable points to an Excel (.xlsx) file on Google Drive.\n"
            "The Google Sheets API only works with native Google Sheets.\n"
            "\n"
            "To resolve this, please convert your Excel file to a Google Sheet:\n"
            "1. Open the Excel file in Google Drive.\n"
            "2. Click File -> Save as Google Sheets.\n"
            "3. Copy the ID of the new Google Sheet from its URL.\n"
            "4. Share the new Google Sheet with your service account email (found in GOOGLE_CREDENTIALS client_email).\n"
            "5. Update your SHEET_ID environment variable in your Replit/deployment settings with the new ID.\n"
            "========================================================================\n"
        )
        raise SystemExit(1)
    else:
        logging.error(f"API Error occurred while opening the spreadsheet: {e}")
        raise e
except SpreadsheetNotFound as e:
    logging.error(
        "\n"
        "========================================================================\n"
        "CONFIG ERROR: The spreadsheet with the given SHEET_ID was not found.\n"
        "\n"
        "Please ensure that:\n"
        "1. The SHEET_ID environment variable is correct.\n"
        "2. You have shared the sheet with your service account email.\n"
        "========================================================================\n"
    )
    raise SystemExit(1)
except Exception as e:
    logging.error(f"Unexpected error loading spreadsheet: {e}")
    raise e


def get_sheet_data() -> list[dict]:
    all_rows = sheet.sheet1.get_all_values()
    if not all_rows:
        return []

    header_idx = 0
    # Detect if row 1 is a title banner (<= 2 non-empty columns) and row 2 has more headers
    r1_non_empty = [val for val in all_rows[0] if val.strip()]
    if len(r1_non_empty) <= 2 and len(all_rows) > 1:
        r2_non_empty = [val for val in all_rows[1] if val.strip()]
        if len(r2_non_empty) > len(r1_non_empty):
            header_idx = 1

    headers = all_rows[header_idx]
    keys = [h.strip() if h.strip() else f"Col_{i+1}" for i, h in enumerate(headers)]

    records = []
    # Data rows start after the header row
    for row in all_rows[header_idx + 1:]:
        # Skip completely empty rows
        if not any(val.strip() for val in row):
            continue
        record = {}
        for i, val in enumerate(row):
            if i < len(keys):
                record[keys[i]] = val.strip()
        records.append(record)

    return records


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("InternalOpsBot running.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        logging.warning(
            f"Ignored message from chat ID {update.effective_chat.id} because it does not match GROUP_ID {GROUP_ID}. "
            f"To allow the bot to respond in this chat, update your GROUP_ID environment variable to {update.effective_chat.id}"
        )
        return

    question = update.message.text.strip()
    if not question:
        return

    try:
        sheet_data = await asyncio.to_thread(get_sheet_data)
    except Exception as e:
        logging.error("Failed to fetch sheet data: %s", e)
        await update.message.reply_text("⚠️ Could not load the knowledge base. Please try again shortly.")
        return

    prompt = (
        "You are an internal operations assistant for an e-commerce moderation team.\n"
        "Answer based strictly on the knowledge base below.\n"
        "If no entry matches, say \"I cannot find an answer in the knowledge base.\"\n"
        "If relevant info is found, answer concisely with references.\n\n"
        f"Knowledge base:\n{json.dumps(sheet_data, indent=2)}\n\n"
        f"Question: {question}\nAnswer:"
    )

    try:
        response = await asyncio.to_thread(
            client.models.generate_content, model=GEMINI_MODEL, contents=prompt
        )
        answer = (response.text or "").strip()
        if not answer:
            raise ValueError("Empty response from Gemini")
    except Exception as e:
        logging.error("Gemini call failed: %s", e)
        await update.message.reply_text("⚠️ Could not generate an answer right now. Please try again.")
        return

    await update.message.reply_text(answer)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self, format, *args):
        pass


def run_health_server(port: int):
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    port = int(os.environ.get("PORT", 8080))
    t = threading.Thread(target=run_health_server, args=(port,), daemon=True)
    t.start()

    app.run_polling()


if __name__ == "__main__":
    main()
