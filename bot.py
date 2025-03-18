import os
import threading
import aiohttp
import re
from datetime import datetime, timedelta
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Environment Variables
API_ID = int(os.getenv("API_ID", "22349465"))  
API_HASH = os.getenv("API_HASH", "3732e079c4125690226d8e7b4e028ca4")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8112458164:AAGGAawWetqBtJGDSUK05Bz6h0wArWCNnno")
FSUB_CHANNEL = os.getenv("FSUB_CHANNEL", "tj_bots")
URL_SHORTENER = "https://indiaearnx.com/st?api=3ca9e6d453fa647f7dea5916f50519819919f62a"
ADMIN_ID = int(os.getenv("ADMIN_ID", "5469498838"))

# Initialize Pyrogram Client
app_bot = Client("TeraboxBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask App for Health Check
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "OK"

def run_flask():
    port = int(os.getenv("PORT", 5000))  
    flask_app.run(host="0.0.0.0", port=port)

# User Tracking Database
user_downloads = {}
premium_users = {}

# ✅ Async Force Subscription Check
async def is_subscribed(client, user_id):
    try:
        chat_member = await client.get_chat_member(FSUB_CHANNEL, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except:
        return False

# ✅ Check if user is premium
def is_premium(user_id):
    if user_id in premium_users and datetime.now() < premium_users[user_id]:
        return True
    return False

# ✅ Add premium user
def add_premium(user_id, duration):
    expiry_date = datetime.now() + duration
    premium_users[user_id] = expiry_date
    return expiry_date

# ✅ Async Function to Extract Direct Video Link from Terabox
async def get_terabox_video_link(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                text = await response.text()
                match = re.search(r'https://d\.terabox\.com/[^\s"]+', text)
                if match:
                    return match.group(0)
    return None

# ✅ /start Command Handler
@app_bot.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id

    if not await is_subscribed(client, user_id):
        await message.reply_text(
            "⚠️ You must join our channel first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{FSUB_CHANNEL}")],
                [InlineKeyboardButton("🔄 Try Again", callback_data="check_fsub")]
            ])
        )
        return

    await message.reply_text(
        "👋 Welcome to Terabox Video Downloader Bot!\n\n"
        "⚡ Send me a Terabox link, and I'll fetch the direct download link for you.\n\n"
        "🆓 First 2 downloads are free. After that, you must verify via a shortener or buy premium.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ])
    )

# ✅ Callback Query Handler
@app_bot.on_callback_query()
async def callback_handler(client, query):
    user_id = query.from_user.id

    if query.data == "check_fsub":
        if await is_subscribed(client, user_id):
            await query.message.edit_text("✅ You have joined the channel! Send a Terabox link now.")
        else:
            await query.answer("❌ You haven't joined yet!", show_alert=True)

    elif query.data == "help":
        await query.message.edit_text("ℹ️ **How to Use:**\n\n"
                                      "1️⃣ Send a Terabox link.\n"
                                      "2️⃣ First 2 downloads are free.\n"
                                      "3️⃣ After that, you must complete short link verification or buy premium.\n\n"
                                      "💡 Contact [Support](https://t.me/your_support_chat) if you have issues.",
                                      disable_web_page_preview=True)

    elif query.data == "buy_premium":
        await query.message.edit_text(
            "💎 **Premium Plans:**\n\n"
            "🔹 1 Day - $1\n"
            "🔹 1 Month - $5\n"
            "🔹 1 Year - $20\n\n"
            "📌 Click below to buy premium and send me the payment proof.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Buy via QR", url="https://your-payment-link.com")],
                [InlineKeyboardButton("🔙 Back", callback_data="start")]
            ])
        )

# ✅ /addpremium Command (Admin Only)
@app_bot.on_message(filters.command("addpremium") & filters.user(ADMIN_ID))
async def add_premium_command(client, message):
    try:
        args = message.text.split()
        if len(args) < 3:
            await message.reply_text("⚠️ Usage: `/addpremium user_id days`")
            return

        user_id = int(args[1])
        days = int(args[2])
        expiry_date = add_premium(user_id, timedelta(days=days))

        await message.reply_text(f"✅ Premium added for User ID: {user_id}\nExpiry: {expiry_date}")

    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

# ✅ Video Download Handler
@app_bot.on_message(filters.text)
async def download_video(client, message):
    user_id = message.from_user.id
    url = message.text.strip()

    if not await is_subscribed(client, user_id):
        await message.reply_text(
            "⚠️ You must join our channel first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{FSUB_CHANNEL}")],
                [InlineKeyboardButton("🔄 Try Again", callback_data="check_fsub")]
            ])
        )
        return

    if is_premium(user_id):
        await message.reply_text("🔄 Fetching your video link...")
        download_link = await get_terabox_video_link(url)

        if download_link:
            await message.reply_text(f"✅ Here is your direct video link:\n\n{download_link}")
        else:
            await message.reply_text("❌ Failed to fetch the video link!")
        return

    if user_id not in user_downloads:
        user_downloads[user_id] = 0

    if user_downloads[user_id] >= 2:
        short_link = f"{URL_SHORTENER}&url={url}"
        await message.reply_text(
            f"🚀 You have used your 2 free downloads.\n\n"
            f"👉 To continue, complete this short link verification: [Verify Here]({short_link})\n\n"
            f"🔹 Or buy premium for unlimited access!",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium")]
            ])
        )
        return

    await message.reply_text("🔄 Fetching your video link...")
    download_link = await get_terabox_video_link(url)

    if download_link:
        user_downloads[user_id] += 1
        await message.reply_text(f"✅ Here is your direct video link:\n\n{download_link}")
    else:
        await message.reply_text("❌ Failed to fetch the video link!")

# ✅ Run Flask and Pyrogram
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()  
    app_bot.run()
