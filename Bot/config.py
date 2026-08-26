import os

def _ids(value: str):
    return [int(x.strip()) for x in value.split(",") if x.strip()]

ADMIN_IDS = _ids(os.getenv("ADMIN_IDS", ""))

START_IMAGE_FILE_ID = os.getenv("START_IMAGE_FILE_ID", "")
SUPPORT_URL = os.getenv("SUPPORT_URL", "")

# Put your Telegram image/file IDs here.
# You can get a file_id by sending the image to your bot and temporarily
# printing message.photo[-1].file_id.
PLANS = {
    "weekly": {
        "name": "📅 Weekly",
        "price": 69,
        "days": 7,
        "duration_text": "7 Days",
        "payment_text": "💳 <b>Deposit Payment</b>",
        "payment_image_file_id": os.getenv("WEEKLY_IMAGE_FILE_ID", ""),
    },
    "quarterly": {
        "name": "📅 Quarterly",
        "price": 150,
        "days": 15,
        "duration_text": "15 Days",
        "payment_text": "💳 <b>Deposit Payment</b>",
        "payment_image_file_id": os.getenv("QUARTERLY_IMAGE_FILE_ID", ""),
    },
    "monthly": {
        "name": "📅 Monthly",
        "price": 250,
        "days": 30,
        "duration_text": "30 Days",
        "payment_text": "💳 <b>Deposit Payment</b>",
        "payment_image_file_id": os.getenv("MONTHLY_IMAGE_FILE_ID", ""),
    },
    "permanent": {
        "name": "♾️ Permanent",
        "price": 350,
        "days": 0,
        "duration_text": "Lifetime",
        "payment_text": "💳 <b>Deposit Payment</b>",
        "payment_image_file_id": os.getenv("PERMANENT_IMAGE_FILE_ID", ""),
    },
}
