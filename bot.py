import requests
import re
import os
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Environment Variables
API_ID = int(os.getenv("API_ID", "22349465"))  # Replace with your API ID
API_HASH = os.getenv("API_HASH", "3732e079c4125690226d8e7b4e028ca4")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8112458164:AAHKTr_OO2zPFoiAZuaS7YnNzmA0444z-kg")
FSUB_CHANNEL = os.getenv("FSUB_CHANNEL", "@tj_bots")
URL_SHORTENER = "https://indiaearnx.com/st?api=3ca9e6d453fa647f7dea5916f50519819919f62a"  # Replace with your URL shortener API
ADMIN_ID = int(os.getenv("ADMIN_ID", "5469498838"))  # Replace with your Telegram user ID

# Initialize Pyrogram Client
app = Client("TeraboxBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Database for user tracking
user_downloads = {}
premium_users = {}

# Function to check force subscription
def is_subscribed(client, user_id):
    try:
        chat_member = client.get_chat_member(FSUB_CHANNEL, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except:
        return False

# Function to check if user is premium
def is_premium(user_id):
    if user_id in premium_users:
        if datetime.now() < premium_users[user_id]:  # Check expiry
            return True
        else:
            del premium_users[user_id]  # Remove expired premium users
    return False

# Function to add premium user
def add_premium(user_id, duration):
    expiry_date = datetime.now() + duration
    premium_users[user_id] = expiry_date
    return expiry_date

# Function to extract direct video link from Terabox
def get_terabox_video_link(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        match = re.search(r'https://d\.terabox\.com/[^\s"]+', response.text)
        if match:
            return match.group(0)  # Return direct video link
    return None

@app.on_message(filters.command("start"))
def start(client, message):
    user_id = message.from_user.id

    if not is_subscribed(client, user_id):
        message.reply_text(
            "⚠️ You must join our channel first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{FSUB_CHANNEL}")],
                [InlineKeyboardButton("🔄 Try Again", callback_data="check_fsub")]
            ])
        )
        return

    message.reply_text(
        "👋 Welcome to Terabox Video Downloader Bot!\n\n"
        "⚡ Send me a Terabox link, and I'll fetch the direct download link for you.\n\n"
        "🆓 First 2 downloads are free. After that, you must verify via a shortener or buy premium.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ])
    )

@app.on_callback_query()
def callback_handler(client, query):
    user_id = query.from_user.id

    if query.data == "check_fsub":
        if is_subscribed(client, user_id):
            query.message.edit_text("✅ You have joined the channel! Send a Terabox link now.")
        else:
            query.answer("❌ You haven't joined yet!", show_alert=True)

    elif query.data == "help":
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

@app.on_message(filters.command("addpremium") & filters.user(ADMIN_ID))
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

@app.on_message(filters.text)
def download_video(client, message):
    user_id = message.from_user.id
    url = message.text.strip()

    if not is_subscribed(client, user_id):
        message.reply_text(
            "⚠️ You must join our channel first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{FSUB_CHANNEL}")],
                [InlineKeyboardButton("🔄 Try Again", callback_data="check_fsub")]
            ])
        )
        return

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

# Run the bot
app.run()



from flask import Flask  
import os  

app = Flask(__name__)  

@app.route("/")  
def home():  
    return "OK"  

if __name__ == "__main__":  
    port = int(os.environ.get("PORT", 8000))  
    app.run(host="0.0.0.0", port=port)




