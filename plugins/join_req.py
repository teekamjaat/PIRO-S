from pyrogram import Client, filters, enums
from pyrogram.types import ChatJoinRequest
from database.users_chats_db import db
from info import ADMINS, AUTH_CHANNEL

@Client.on_chat_join_request(filters.chat(AUTH_CHANNEL))
async def join_reqs(client, message: ChatJoinRequest):
  if not await db.find_join_req(message.from_user.id):
    await db.add_join_req(message.from_user.id)

@Client.on_message(filters.command("delreq") & filters.private & filters.user(ADMINS))
async def del_requests(client, message):
    await db.del_join_req()    
    await message.reply("<b>⚙ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ᴄʜᴀɴɴᴇʟ ʟᴇғᴛ ᴜꜱᴇʀꜱ ᴅᴇʟᴇᴛᴇᴅ</b>")

# ==== OLD CODE START ====
# (Your existing join_req.py code remains here)
# ==== OLD CODE END ====

# ==== MODIFIED CODE START ====
# Multiple Force Subscription Feature
FORCE_SUB_CHANNELS = ["channel_1", "channel_2", "channel_3"]

async def check_subscription(user_id):
    for channel in FORCE_SUB_CHANNELS:
        member = await bot.get_chat_member(channel, user_id)
        if member.status not in ["member", "administrator", "creator"]:
            return False, channel
    return True, None

@bot.on_message(filters.private)
async def force_sub_check(client, message):
    is_subscribed, channel = await check_subscription(message.from_user.id)
    if not is_subscribed:
        join_link = await bot.export_chat_invite_link(channel)
        await message.reply(f"🚀 Please join [this channel]({join_link}) to use the bot.")
        return
    await message.continue_propagation()
# ==== MODIFIED CODE END ====
