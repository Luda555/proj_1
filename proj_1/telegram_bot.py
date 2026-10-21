
import os
import logging

from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    JobQueue,
)
from telegram.error import InvalidToken

from telegram_storage import load_data, save_data

async def send_appointment_reminders(
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send reminders for appointments scheduled for tomorrow."""
    data = load_data()

    tomorrow = (
        datetime.now(ZoneInfo("Europe/Kyiv")).date()
        + timedelta(days=1)
    ).isoformat()

    # Find linked Telegram accounts by phone number.
    phone_to_telegram = {
        client_data.get("phone"): telegram_id
        for telegram_id, client_data in data["clients"].items()
        if client_data.get("phone")
    }

    for index, appointment in enumerate(data.get("appointments", [])):
        if appointment.get("date") != tomorrow:
            continue

        if appointment.get("status") != "Scheduled":
            continue

        phone = appointment.get("phone")
        telegram_id = phone_to_telegram.get(phone)

        if not telegram_id:
            continue

        # Prevent sending the same reminder more than once.
        if appointment.get("reminder_sent"):
            continue

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    " Підтвердити",
                    callback_data=f"confirm:{index}",
                ),
                InlineKeyboardButton(
                    " Скасувати",
                    callback_data=f"cancel:{index}",
                ),
            ]
        ])

        try:
            await context.bot.send_message(
                chat_id=int(telegram_id),
                text=(
                    " Нагадування від Beauty Clinic!\n\n"
                    f"Ваш запис на завтра, {tomorrow}.\n"
                    f"Час: {appointment.get('start_time', 'не вказано')}\n\n"
                    "Будь ласка, підтвердіть або скасуйте візит."
                ),
                reply_markup=keyboard,
            )

            appointment["reminder_sent"] = True

        except Exception:
            logging.exception(
                "Could not send reminder for phone %s",
                phone,
            )

    save_data(data)


async def handle_appointment_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle appointment confirmation or cancellation."""
    query = update.callback_query

    if query is None or query.data is None:
        return

    await query.answer()

    try:
        action, index_text = query.data.split(":", 1)
        index = int(index_text)
    except (ValueError, TypeError):
        await query.edit_message_text(
            "Не вдалося визначити запис. Спробуйте звернутися до адміністратора."
        )
        return

    data = load_data()
    appointments = data.get("appointments", [])

    if not 0 <= index < len(appointments):
        await query.edit_message_text(
            "Запис не знайдено. Зверніться до адміністратора."
        )
        return

    appointment = appointments[index]

    if appointment.get("status") != "Scheduled":
        await query.edit_message_text(
            "Цей запис уже скасовано або його статус змінено."
        )
        return

    if action == "confirm":
        appointment["confirmed"] = True
        message = " Дякуємо! Ваш запис підтверджено."
    elif action == "cancel":
        appointment["status"] = "Cancelled"
        message = " Ваш запис скасовано."
    else:
        await query.edit_message_text(
            "Невідома дія. Зверніться до адміністратора."
        )
        return

    save_data(data)
    await query.edit_message_text(message)



load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.CRITICAL,
)

logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("telegram").setLevel(logging.CRITICAL)
logging.getLogger("telegram.ext").setLevel(logging.CRITICAL)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    data = load_data()
    telegram_id = str(user.id)

    # Preserve a phone number if the account was already linked.
    client_data = data["clients"].get(telegram_id, {})
    client_data.update({
        "first_name": user.first_name,
        "username": user.username,
    })
    data["clients"][telegram_id] = client_data
    save_data(data)

    first_name = user.first_name or "client"

    await message.reply_text(
        f"Welcome to Beauty Clinic, {first_name}! 🌸\n\n"
        f"Your Telegram ID: {user.id}\n\n"
        "You will now be able to receive reminders "
        "about your appointments and confirm your visits."
    )


async def link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    if len(context.args) != 1:
        await message.reply_text(
            "Please use the command like this:\n"
            "/link YOUR_CODE"
        )
        return

    code = context.args[0].strip().upper()
    data = load_data()
    link_info = data["link_codes"].get(code)

    if link_info is None:
        await message.reply_text(
            "Invalid or expired linking code. "
            "Please check the code and try again."
        )
        return

    phone = link_info["phone"]

    data["clients"][str(user.id)] = {
        "first_name": user.first_name,
        "username": user.username,
        "phone": phone,
    }

    del data["link_codes"][code]
    save_data(data)

    await message.reply_text(
        "Your Telegram account has been linked "
        "successfully to Beauty Clinic! 🌸"
    )


def main() -> None:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not found")

    app = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("link", link))
    app.add_handler(
        CallbackQueryHandler(handle_appointment_response)
    )
    
    if app.job_queue is None:
        raise RuntimeError(
            'JobQueue недоступний. '
            'Встанови: python -m pip install "python-telegram-bot[job-queue]"'
        )

    app.job_queue.run_daily(
        send_appointment_reminders,
        time=datetime.strptime("10:00", "%H:%M").time().replace(
            tzinfo=ZoneInfo("Europe/Kyiv")
        ),
        name="appointment_reminders",
    )

    print("Beauty Clinic Telegram bot is running...")

    try:
        app.run_polling()
    except InvalidToken:
        print(
            "Telegram authorization error. "
            "Please check the token in .env. "
            "The token is hidden."
        )


if __name__ == "__main__":
    main()

