
import asyncio
import copy
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from zoneinfo import ZoneInfo

import telegram_bot




@pytest.fixture
def storage(monkeypatch):
    """Use test data instead of the real telegram_data.json."""
    data = {
        "clients": {
            "1028136169": {
                "first_name": "Luda",
                "phone": "0939892948"
            }
        },
        "link_codes": {},
        "appointments": []
    }

    saved_data = []

    monkeypatch.setattr(
        telegram_bot,
        "load_data",
        lambda: data
    )

    monkeypatch.setattr(
        telegram_bot,
        "save_data",
        lambda value: saved_data.append(copy.deepcopy(value))
    )

    return data, saved_data


def run_async(coroutine):
    """Run an async function without requiring pytest-asyncio."""
    return asyncio.run(coroutine)


def make_appointment(date, status="Scheduled", **kwargs):
    appointment = {
        "phone": "0939892948",
        "date": date,
        "start_time": "12:30",
        "status": status
    }
    appointment.update(kwargs)
    return appointment


def make_callback(data, telegram_id=1028136169):
    query = SimpleNamespace(
        data=data,
        from_user=SimpleNamespace(id=telegram_id),
        answer=AsyncMock(),
        edit_message_text=AsyncMock()
    )

    update = SimpleNamespace(callback_query=query)

    return update, query


# -------------------------
# Appointment reminders
# -------------------------

def test_reminder_is_sent_for_tomorrow(storage):
    data, saved_data = storage

    tomorrow = (
        datetime.now(ZoneInfo("Europe/Kyiv")).date()
        + timedelta(days=1)
    )

    data["appointments"].append(
        make_appointment(tomorrow.isoformat())
    )

    context = SimpleNamespace(
        bot=SimpleNamespace(send_message=AsyncMock())
    )

    run_async(
        telegram_bot.send_appointment_reminders(context)
    )

    context.bot.send_message.assert_awaited_once()

    assert data["appointments"][0]["reminder_sent"] is True
    assert saved_data


def test_reminder_is_not_sent_for_past_appointment(storage):
    data, _ = storage

    yesterday = (
        datetime.now(ZoneInfo("Europe/Kyiv")).date()
        - timedelta(days=1)
    )

    data["appointments"].append(
        make_appointment(yesterday.isoformat())
    )

    context = SimpleNamespace(
        bot=SimpleNamespace(send_message=AsyncMock())
    )

    run_async(
        telegram_bot.send_appointment_reminders(context)
    )

    context.bot.send_message.assert_not_awaited()


def test_reminder_is_not_sent_for_cancelled_appointment(storage):
    data, _ = storage

    tomorrow = (
        datetime.now(ZoneInfo("Europe/Kyiv")).date()
        + timedelta(days=1)
    )

    data["appointments"].append(
        make_appointment(tomorrow.isoformat(), status="Cancelled")
    )

    context = SimpleNamespace(
        bot=SimpleNamespace(send_message=AsyncMock())
    )

    run_async(
        telegram_bot.send_appointment_reminders(context)
    )

    context.bot.send_message.assert_not_awaited()


def test_reminder_is_not_sent_twice(storage):
    data, _ = storage

    tomorrow = (
        datetime.now(ZoneInfo("Europe/Kyiv")).date()
        + timedelta(days=1)
    )

    data["appointments"].append(
        make_appointment(
            tomorrow.isoformat(),
            reminder_sent=True
        )
    )

    context = SimpleNamespace(
        bot=SimpleNamespace(send_message=AsyncMock())
    )

    run_async(
        telegram_bot.send_appointment_reminders(context)
    )

    context.bot.send_message.assert_not_awaited()


def test_reminder_is_not_sent_without_telegram_account(storage):
    data, _ = storage

    data["clients"] = {}

    tomorrow = (
        datetime.now(ZoneInfo("Europe/Kyiv")).date()
        + timedelta(days=1)
    )

    data["appointments"].append(
        make_appointment(tomorrow.isoformat())
    )

    context = SimpleNamespace(
        bot=SimpleNamespace(send_message=AsyncMock())
    )

    run_async(
        telegram_bot.send_appointment_reminders(context)
    )

    context.bot.send_message.assert_not_awaited()


# -------------------------
# Appointment confirmation
# -------------------------

def test_client_can_confirm_own_appointment(storage):
    data, saved_data = storage

    data["appointments"].append(
        make_appointment("2026-12-20")
    )

    update, query = make_callback("confirm:0")

    run_async(
        telegram_bot.handle_appointment_response(
            update,
            SimpleNamespace()
        )
    )

    assert data["appointments"][0]["confirmed"] is True
    assert data["appointments"][0]["status"] == "Scheduled"
    assert saved_data

    query.answer.assert_awaited_once()
    query.edit_message_text.assert_awaited_once()


def test_client_can_cancel_own_appointment(storage):
    data, saved_data = storage

    data["appointments"].append(
        make_appointment("2026-12-20")
    )

    update, query = make_callback("cancel:0")

    run_async(
        telegram_bot.handle_appointment_response(
            update,
            SimpleNamespace()
        )
    )

    assert data["appointments"][0]["status"] == "Cancelled"
    assert saved_data

    query.answer.assert_awaited_once()
    query.edit_message_text.assert_awaited_once()


def test_another_client_cannot_change_appointment(storage):
    data, saved_data = storage

    data["appointments"].append(
        make_appointment("2026-12-20")
    )

    update, query = make_callback(
        "cancel:0",
        telegram_id=999999999
    )

    run_async(
        telegram_bot.handle_appointment_response(
            update,
            SimpleNamespace()
        )
    )

    assert data["appointments"][0]["status"] == "Scheduled"
    assert "confirmed" not in data["appointments"][0]
    assert saved_data == []

    query.answer.assert_awaited_once()
    query.edit_message_text.assert_awaited_once()


def test_client_cannot_change_already_cancelled_appointment(storage):
    data, _ = storage

    data["appointments"].append(
        make_appointment(
            "2026-12-20",
            status="Cancelled"
        )
    )

    update, query = make_callback("confirm:0")

    run_async(
        telegram_bot.handle_appointment_response(
            update,
            SimpleNamespace()
        )
    )

    assert data["appointments"][0]["status"] == "Cancelled"
    assert "confirmed" not in data["appointments"][0]

    query.answer.assert_awaited_once()
    query.edit_message_text.assert_awaited_once()


def test_invalid_appointment_index_is_handled(storage):
    data, _ = storage

    update, query = make_callback("confirm:10")

    run_async(
        telegram_bot.handle_appointment_response(
            update,
            SimpleNamespace()
        )
    )

    assert data["appointments"] == []

    query.answer.assert_awaited_once()
    query.edit_message_text.assert_awaited_once()

# -------------------------
# Additional Telegram tests
# -------------------------

def test_reminder_send_error_does_not_mark_as_sent(storage):
    data, _ = storage

    tomorrow = (
        datetime.now(ZoneInfo("Europe/Kyiv")).date()
        + timedelta(days=1)
    ).isoformat()

    data["appointments"].append(
        make_appointment(tomorrow)
    )

    context = SimpleNamespace(
        bot=SimpleNamespace(
            send_message=AsyncMock(
                side_effect=Exception("Telegram connection error")
            )
        )
    )

    run_async(
        telegram_bot.send_appointment_reminders(context)
    )

    assert "reminder_sent" not in data["appointments"][0]

def test_invalid_callback_data_is_handled(storage):
    data, _ = storage
    data["appointments"].append(
        make_appointment("2026-12-20")
    )

    update, query = make_callback("invalid_data")

    run_async(
        telegram_bot.handle_appointment_response(
            update,
            SimpleNamespace()
        )
    )

    assert data["appointments"][0]["status"] == "Scheduled"
    assert "confirmed" not in data["appointments"][0]

    query.answer.assert_awaited_once()
    query.edit_message_text.assert_awaited_once()


def test_unknown_callback_action_is_handled(storage):
    data, _ = storage
    data["appointments"].append(
        make_appointment("2026-12-20")
    )

    update, query = make_callback("unknown:0")

    run_async(
        telegram_bot.handle_appointment_response(
            update,
            SimpleNamespace()
        )
    )

    assert data["appointments"][0]["status"] == "Scheduled"
    assert "confirmed" not in data["appointments"][0]

    query.answer.assert_awaited_once()
    query.edit_message_text.assert_awaited_once()