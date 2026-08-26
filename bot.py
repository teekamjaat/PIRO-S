import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from dotenv import load_dotenv

from bot.config import ADMIN_IDS, PLANS, START_IMAGE_FILE_ID, SUPPORT_URL
from bot.db import init_db, get_user, upsert_user, create_pending, get_pending, set_pending_status, activate_premium
from bot.keyboards import main_menu, plans_menu, payment_menu, admin_payment_menu, back_menu
from bot.utils import format_expiry, now_ist

load_dotenv()

logging.basicConfig(level=logging.INFO)
router = Router()


@router.message(CommandStart())
async def start(message: Message):
    await upsert_user(message.from_user.id, message.from_user.username, message.from_user.full_name)

    text = (
        "🥵 <b>ALL THE PREMIUM STUFFS</b>\n\n"
        "⚡ <b>Instant Access Available For You!</b>\n"
        "👇 <b>Click and claim your deal now!</b>"
    )

    if START_IMAGE_FILE_ID:
        await message.answer_photo(
            START_IMAGE_FILE_ID,
            caption=text,
            reply_markup=main_menu()
        )
    else:
        await message.answer(text, reply_markup=main_menu())


@router.callback_query(F.data == "plans")
async def show_plans(callback: CallbackQuery):
    await callback.answer()
    text = "💎 <b>Premium Plans</b>\n\nChoose your plan below:"
    await callback.message.answer(text, reply_markup=plans_menu(PLANS))


@router.callback_query(F.data == "back_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🏠 <b>Main Menu</b>",
        reply_markup=main_menu()
    )


@router.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    await callback.answer()
    user = await get_user(callback.from_user.id)

    if not user:
        await callback.message.answer("Please use /start first.")
        return

    expiry = user.get("premium_until")
    if expiry:
        await callback.message.answer(
            f"👤 <b>My Profile</b>\n\n"
            f"🆔 User ID: <code>{callback.from_user.id}</code>\n"
            f"💎 Premium: <b>Active</b>\n"
            f"⏳ Valid Until: <b>{format_expiry(expiry)}</b>",
            reply_markup=back_menu()
        )
    else:
        await callback.message.answer(
            f"👤 <b>My Profile</b>\n\n"
            f"🆔 User ID: <code>{callback.from_user.id}</code>\n"
            f"💎 Premium: <b>Not Active</b>",
            reply_markup=back_menu()
        )


@router.callback_query(F.data == "support")
async def support(callback: CallbackQuery):
    await callback.answer()
    if SUPPORT_URL:
        await callback.message.answer(
            "💬 <b>Support</b>\n\nClick below to contact support.",
            reply_markup=back_menu()
        )
    else:
        await callback.message.answer(
            "💬 <b>Support</b>\n\nPlease contact the administrator.",
            reply_markup=back_menu()
        )


@router.callback_query(F.data.startswith("plan:"))
async def select_plan(callback: CallbackQuery):
    await callback.answer()
    plan_id = callback.data.split(":", 1)[1]
    plan = PLANS.get(plan_id)

    if not plan:
        await callback.message.answer("❌ Plan not found.")
        return

    await create_pending(callback.from_user.id, plan_id)

    caption = (
        f"{plan['payment_text']}\n\n"
        f"💰 <b>Amount:</b> ₹{plan['price']}\n"
        f"⏳ <b>Duration:</b> {plan['duration_text']}"
    )

    image = plan.get("payment_image_file_id")
    if image:
        await callback.message.answer_photo(
            image,
            caption=caption,
            reply_markup=payment_menu(plan_id)
        )
    else:
        await callback.message.answer(
            caption + "\n\n⚠️ Payment image is not configured.",
            reply_markup=payment_menu(plan_id)
        )


@router.callback_query(F.data.startswith("verify:"))
async def verify_start(callback: CallbackQuery):
    await callback.answer()
    plan_id = callback.data.split(":", 1)[1]

    pending = await get_pending(callback.from_user.id)
    if not pending or pending.get("plan_id") != plan_id or pending.get("status") != "awaiting_screenshot":
        await create_pending(callback.from_user.id, plan_id)

    await callback.message.answer(
        "📸 <b>Send Your Payment Screenshot</b>\n\n"
        "Please send a clear screenshot of your successful payment.\n"
        "Your screenshot will be sent to the admin for manual verification."
    )


@router.message(F.photo)
async def receive_screenshot(message: Message):
    pending = await get_pending(message.from_user.id)

    if not pending or pending.get("status") != "awaiting_screenshot":
        return

    plan = PLANS.get(pending["plan_id"])
    if not plan:
        await message.answer("❌ The selected plan is no longer available.")
        return

    photo = message.photo[-1]
    await set_pending_status(
        message.from_user.id,
        "pending_admin",
        screenshot_file_id=photo.file_id
    )

    await message.answer(
        "✅ <b>Screenshot Submitted!</b>\n\n"
        "Your payment is now pending manual verification. "
        "Please wait for admin approval."
    )

    username = f"@{message.from_user.username}" if message.from_user.username else "No username"
    admin_text = (
        "🔔 <b>New Payment Verification</b>\n\n"
        f"👤 <b>User:</b> {username}\n"
        f"🆔 <b>User ID:</b> <code>{message.from_user.id}</code>\n"
        f"📦 <b>Plan:</b> {plan['name']}\n"
        f"💰 <b>Amount:</b> ₹{plan['price']}\n"
        f"🕐 <b>Submitted:</b> {now_ist().strftime('%d-%m-%Y %I:%M:%S %p')}"
    )

    bot = message.bot
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                admin_id,
                photo.file_id,
                caption=admin_text,
                reply_markup=admin_payment_menu(message.from_user.id)
            )
        except Exception:
            logging.exception("Could not notify admin %s", admin_id)


@router.callback_query(F.data.startswith("approve:"))
async def approve_payment(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Not authorized.", show_alert=True)
        return

    await callback.answer()
    user_id = int(callback.data.split(":", 1)[1])
    pending = await get_pending(user_id)

    if not pending or pending.get("status") != "pending_admin":
        await callback.message.answer("⚠️ This payment request is already processed.")
        return

    plan = PLANS.get(pending["plan_id"])
    if not plan:
        await callback.message.answer("❌ Plan configuration not found.")
        return

    expiry = await activate_premium(user_id, plan["days"])
    await set_pending_status(user_id, "approved")

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"✅ <b>Payment Approved</b>\n\n"
        f"👤 User ID: <code>{user_id}</code>\n"
        f"📦 Plan: {plan['name']}\n"
        f"💰 Amount: ₹{plan['price']}"
    )

    try:
        await callback.bot.send_message(
            user_id,
            f"🎉 <b>Payment Verified Successfully!</b>\n\n"
            f"💎 Plan: <b>{plan['name']}</b>\n"
            f"💰 Amount: ₹{plan['price']}\n"
            f"⏳ Valid Until: <b>{format_expiry(expiry)}</b>"
        )
    except Exception:
        logging.exception("Could not notify user %s", user_id)


@router.callback_query(F.data.startswith("reject:"))
async def reject_payment(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Not authorized.", show_alert=True)
        return

    await callback.answer()
    user_id = int(callback.data.split(":", 1)[1])
    pending = await get_pending(user_id)

    if not pending or pending.get("status") != "pending_admin":
        await callback.message.answer("⚠️ This payment request is already processed.")
        return

    await set_pending_status(user_id, "rejected")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"❌ <b>Payment Rejected</b>\n\nUser ID: <code>{user_id}</code>"
    )

    try:
        await callback.bot.send_message(
            user_id,
            "❌ <b>Payment Rejected</b>\n\n"
            "Your payment screenshot could not be verified. "
            "Please make a new payment and submit a clear screenshot."
        )
    except Exception:
        logging.exception("Could not notify user %s", user_id)


async def healthcheck(request):
    return web.Response(text="OK")


async def run_health_server():
    port = int(os.getenv("PORT", "8000"))
    app = web.Application()
    app.router.add_get("/", healthcheck)
    app.router.add_get("/health", healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info("Health server listening on %s", port)


async def main():
    await init_db()

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is missing")

    bot = Bot(
        token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await run_health_server()
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
    
    
    @router.message(F.photo)
async def get_file_id(message: Message):
    file_id = message.photo[-1].file_id
    await message.reply(
        f"📸 File ID:\n\n<code>{file_id}</code>"
    )
