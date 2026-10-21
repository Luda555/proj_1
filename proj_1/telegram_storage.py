
import json
from pathlib import Path

STORAGE_FILE = Path(__file__).resolve().parent / "telegram_data.json"


def load_data():
    if not STORAGE_FILE.exists():
        return {"clients": {}, "link_codes": {}, "appointments": []}

    try:
        with STORAGE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {"clients": {}, "link_codes": {}, "appointments": []}

    data.setdefault("clients", {})
    data.setdefault("appointments", [])
    data.setdefault("link_codes", {})
    return data


def save_data(data):
    with STORAGE_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


import secrets
import string


def create_link_code():
    """Generate a random code for linking a client to Telegram."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))

