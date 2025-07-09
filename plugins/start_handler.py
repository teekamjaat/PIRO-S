from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.command("start") & filters.private)
async def custom_start(client, message: Message):
    args = message.text.split()
    
    if len(args) > 1 and args[1] == "hello":
        await message.reply_text("👋 Welcome from the special link!")
    else:
        await message.reply_text("Hello! How can I help you?")
