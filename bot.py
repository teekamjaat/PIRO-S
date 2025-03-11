from pyrogram import Client, __version__, filters
from pyrogram.raw.all import layer
from database.ia_filterdb import Media
from database.users_chats_db import db
from info import API_ID, API_HASH, ADMINS, BOT_TOKEN, LOG_CHANNEL, PORT, SUPPORT_GROUP
from utils import temp
from typing import Union, Optional, AsyncGenerator
from pyrogram import types
from Script import script 
from datetime import date, datetime 
import datetime
import pytz
from aiohttp import web
from plugins import web_server, check_expired_premium
import asyncio
import time

class Bot(Client):
    def __init__(self):
        super().__init__(
            name='aks',
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            sleep_threshold=5,
            workers=150,
            plugins={"root": "plugins"}
        )
        

@bot.on_message(filters.command("start") & filters.private)
async def start(bot, message):
    """
    Handles the /start command and checks for subscription.
    """
    if not await send_subscription_message(bot, message):
        return  # Stop execution if user is not subscribed

    await message.reply_text("🎉 Welcome! You have full access to the bot.")
    async def stop(self, *args):
        await super().stop()
        print("Bot stopped.")
    
    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        """Iterate through a chat sequentially.
        This convenience method does the same as repeatedly calling :meth:`~pyrogram.Client.get_messages` in a loop, thus saving
        you from the hassle of setting up boilerplate code. It is useful for getting the whole chat messages with a
        single call.
        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.
                For your personal cloud (Saved Messages) you can simply use "me" or "self".
                For a contact that exists in your Telegram address book you can use his phone number (str).
                
            limit (``int``):
                Identifier of the last message to be returned.
                
            offset (``int``, *optional*):
                Identifier of the first message to be returned.
                Defaults to 0.
        Returns:
            ``Generator``: A generator yielding :obj:`~pyrogram.types.Message` objects.
        Example:
            .. code-block:: python
                for message in app.iter_messages("pyrogram", 1, 15000):
                    print(message.text)
        """
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1

app = Bot()
app.run()
