import os
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
import gspread

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GROUP_ID = int(os.environ["GROUP_ID"])
SHEET_ID = os.environ["SHEET_ID"]

client = genai.Client(api_key=GEMINI_API_KEY)

gc = gspread.service_account_from_dict(json.loads(os.environ["GOOGLE_CREDENTIALS"]))
sheet = gc.open_by_key(SHEET_ID)

def get_sheet_data() -> list[dict]:
    return sheet.sheet1.get_all_records()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("InternalOpsBot running.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return

    question = update.message.text.strip()
    if not question:
        return

    sheet_data = get_sheet_data()

    prompt = (
        "You are an internal operations assistant for an e-commerce moderation team.\n"
        "Answer based strictly on the knowledge base below.\n"
        "If no entry matches, say \"I cannot find an answer in the knowledge base.\"\n"
        "If relevant info is found, answer concisely with references.\n\n"
        f"Knowledge base:\n{json.dumps(sheet_data, indent=2)}\n\n"
        f"Question: {question}\nAnswer:"
    )

    response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    answer = response.text.strip()

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
