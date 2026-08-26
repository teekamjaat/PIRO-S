import os
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient

_client = None
_db = None


async def init_db():
    global _client, _db
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI is missing")

    _client = AsyncIOMotorClient(uri)
    _db = _client[os.getenv("MONGODB_DB", "premium_bot")]

    await _db.users.create_index("user_id", unique=True)
    await _db.payments.create_index("user_id")
    await _db.payments.create_index("status")


async def upsert_user(user_id, username, full_name):
    await _db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "username": username,
                "full_name": full_name,
                "updated_at": datetime.now(timezone.utc)
            },
            "$setOnInsert": {
                "user_id": user_id,
                "premium_until": None,
                "created_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )


async def get_user(user_id):
    return await _db.users.find_one({"user_id": user_id})


async def create_pending(user_id, plan_id):
    await _db.payments.update_one(
        {"user_id": user_id, "status": {"$in": ["awaiting_screenshot", "pending_admin"]}},
        {"$set": {
            "status": "cancelled",
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=False
    )

    await _db.payments.insert_one({
        "user_id": user_id,
        "plan_id": plan_id,
        "status": "awaiting_screenshot",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    })


async def get_pending(user_id):
    return await _db.payments.find_one(
        {"user_id": user_id, "status": {"$in": ["awaiting_screenshot", "pending_admin"]}},
        sort=[("created_at", -1)]
    )


async def set_pending_status(user_id, status, screenshot_file_id=None):
    update = {
        "$set": {
            "status": status,
            "updated_at": datetime.now(timezone.utc)
        }
    }
    if screenshot_file_id:
        update["$set"]["screenshot_file_id"] = screenshot_file_id

    await _db.payments.update_one(
        {"user_id": user_id, "status": {"$in": ["awaiting_screenshot", "pending_admin"]}},
        update,
        sort=[("created_at", -1)]
    )


async def activate_premium(user_id, days):
    now = datetime.now(timezone.utc)
    user = await get_user(user_id)
    current = user.get("premium_until") if user else None

    if days == 0:
        expiry = datetime(9999, 12, 31, tzinfo=timezone.utc)
    else:
        if current and current > now and current.year < 9999:
            start = current
        else:
            start = now
        expiry = start + timedelta(days=days)

    await _db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "premium_until": expiry,
            "updated_at": now
        }},
        upsert=True
    )
    return expiry
