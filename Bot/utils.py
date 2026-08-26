from datetime import datetime, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def now_ist():
    return datetime.now(timezone.utc).astimezone(IST)


def format_expiry(value):
    if not value:
        return "Not Active"

    if value.year >= 9999:
        return "Lifetime"

    return value.astimezone(IST).strftime("%d-%m-%Y %I:%M:%S %p")
