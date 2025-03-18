import os
import threading
import requests
import re
from datetime import datetime, timedelta
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Environment Variables
API_ID = int(os.getenv("API_ID", "22349465"))  
API_HASH = os.getenv("API_HASH", "3732e079c4125690226d8e7b4e028ca4")
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")  
URL_SHORTENER = "https://indiaearnx.com/st?api=YOUR_SHORTENER_API"  
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

# Function to check if user is premium
def is_premium(user_id):
    if user_id in premium_users:
        if datetime.now() < premium_users[user_id]:  
            return True
        else:
            del premium_users[user_id]  
    return False

# Function to add premium user
def add_premium(user_id, duration):
    expiry_date = datetime.now() + duration
    premium_users[user_id] = expiry_date
    return expiry_date

# Function to extract direct video link from Terabox
def get_terabox_video_link(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"❌ Failed to fetch page: {response.status_code}")
            return None

        print(f"🔍 Terabox Page Fetched Successfully!\n{response.text[:500]}")  

        # Extract direct video link (Update regex if needed)
        match = re.search(r'https://d\.terabox\.com/[^\s"]+', response.text)
        if match:
            direct_link = match.group(0)
            print(f"✅ Extracted Direct Link: {direct_link}")  
            return direct_link
        else:
            print("❌ No direct link found in the page.")
            return None

    except Exception as e:
        print(f"⚠️ Error fetching Terabox link: {e}")
        return None

# Telegram Bot Handlers
@app_bot.on_message(filters.command("start"))
def start(client, message):
    user_id = message.from_user.id

    message.reply_text(
        "👋 Welcome to Terabox Video Downloader Bot!\n\n"
        "⚡ Send me a Terabox link, and I'll fetch the direct download link for you.\n\n"
        "🆓 First 2 downloads are free. After that, you must verify via a shortener or buy premium.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ])
    )

@app_bot.on_callback_query()
def callback_handler(client, query):
    user_id = query.from_user.id

    if query.data == "help":
        query.message.edit_text("ℹ️ How to Use:\n\n"
                                "1️⃣ Send a Terabox link.\n"
                                "2️⃣ First 2 downloads are free.\n"
                                "3️⃣ After that, you must complete short link verification or buy premium.\n\n"
                                "💡 Contact [Support](https://t.me/your_support_chat) if you have issues.",
                                disable_web_page_preview=True)

    elif query.data == "buy_premium":
        query.message.edit_text(
            "💎 Premium Plans:\n\n"
            "🔹 1 Day - $1\n"
            "🔹 1 Month - $5\n"
            "🔹 1 Year - $20\n\n"
            "📌 Click below to buy premium and send me the payment proof.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Buy via QR", url="https://your-payment-link.com")],
                [InlineKeyboardButton("🔙 Back", callback_data="start")]
            ])
        )

@app_bot.on_message(filters.command("addpremium") & filters.user(ADMIN_ID))
def add_premium_command(client, message):
    try:
        args = message.text.split()
        if len(args) < 3:
            message.reply_text("⚠️ Usage: /addpremium user_id days")
            return

        user_id = int(args[1])
        days = int(args[2])
        expiry_date = add_premium(user_id, timedelta(days=days))

        message.reply_text(f"✅ Premium added for User ID: {user_id}\nExpiry: {expiry_date}")

    except Exception as e:
        message.reply_text(f"❌ Error: {str(e)}")

@app_bot.on_message(filters.text)
def download_video(client, message):
    user_id = message.from_user.id
    url = message.text.strip()

    if is_premium(user_id):
        message.reply_text("🔄 Fetching your video link...")
        download_link = get_terabox_video_link(url)

        if download_link:
            message.reply_text(f"✅ Here is your direct video link:\n\n{download_link}")
        else:
            message.reply_text("❌ Failed to fetch the video link!")
        return

    if user_id not in user_downloads:
        user_downloads[user_id] = 0

    if user_downloads[user_id] >= 2:
        short_link = requests.get(URL_SHORTENER + url).text  
        message.reply_text(
            f"🚀 You have used your 2 free downloads.\n\n"
            f"👉 To continue, complete this short link verification: [Verify Here]({short_link})\n\n"
            f"🔹 Or buy premium for unlimited access!",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium")]
            ])
        )
        return

    message.reply_text("🔄 Fetching your video link...")
    download_link = get_terabox_video_link(url)

    if download_link:
        user_downloads[user_id] += 1
        message.reply_text(f"✅ Here is your direct video link:\n\n{download_link}")
    else:
        message.reply_text("❌ Failed to fetch the video link!")

# Run Flask and Pyrogram in Parallel
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()  
    app_bot.run()
