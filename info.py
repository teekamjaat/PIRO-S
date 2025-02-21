import re
import os
from os import environ
from pyrogram import enums
from Script import script
import asyncio
import json
from collections import defaultdict
from pyrogram import Client

id_pattern = re.compile(r'^.\d+$')
def is_enabled(value, default):
    if value.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif value.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        return default

#main variables
SESSION = environ.get('SESSION', 'Media_search')
API_ID = int(environ.get('API_ID', ''))
API_HASH = environ.get('API_HASH', '')
BOT_TOKEN = environ.get('BOT_TOKEN', '')
ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '5469498838').split()]
USERNAME = environ.get('USERNAME', 'https://telegram.me/teekam_jaat')
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '-1001786924542'))
CHANNELS = [int(ch) if id_pattern.search(ch) else ch for ch in environ.get('CHANNELS', '-1001983152794 -1001756564118 -1002369988753').split()]
DATABASE_URI = environ.get('DATABASE_URI', "mongodb+srv://Ipopcornbot:ipopcornbot@ipopcornbot.c0tws.mongodb.net/?retryWrites=true&w=majority&appName=Ipopcornbot")
DATABASE_URI2 = environ.get('DATABASE_URI2', "mongodb+srv://teekam9079:teekam@teekam.7eu6m.mongodb.net/?retryWrites=true&w=majority&appName=Teekam")
DATABASE_NAME = environ.get('DATABASE_NAME', "tjbot")
COLLECTION_NAME = environ.get('COLLECTION_NAME', 'tjbotdatabase')
LOG_API_CHANNEL = int(environ.get('LOG_API_CHANNEL', '-1001786924542'))
QR_CODE = environ.get('QR_CODE', 'https://envs.sh/hNt.jpg')

#this vars is for when heroku or koyeb acc get banned, then change this vars as your file to link bot name
BIN_CHANNEL = int(environ.get('BIN_CHANNEL', '-1001786924542'))
URL = environ.get('URL', '')

# verify system vars
IS_VERIFY = is_enabled('IS_VERIFY', True)
LOG_VR_CHANNEL = int(environ.get('LOG_VR_CHANNEL', '-1001786924542'))
TUTORIAL = environ.get("TUTORIAL", "https://t.me/How_To_Download_Movie_Video/7")
TUTORIAL2 = environ.get("TUTORIAL2", "https://t.me/How_To_Download_Movie_Video/7")
TUTORIAL3 = environ.get("TUTORIAL3", "https://t.me/How_To_Download_Movie_Video/7")
VERIFY_IMG = environ.get("VERIFY_IMG", "https://graph.org/file/45a270fc6a0a1c183c614.jpg")
SHORTENER_API = environ.get("SHORTENER_API", "caa6a48f69b08a00a8e18f5a28c5250f3e75fe27")
SHORTENER_WEBSITE = environ.get("SHORTENER_WEBSITE", "anylinks.in")
SHORTENER_API2 = environ.get("SHORTENER_API2", "3ca9e6d453fa647f7dea5916f50519819919f62a")
SHORTENER_WEBSITE2 = environ.get("SHORTENER_WEBSITE2", "indiaearnx.com")
SHORTENER_API3 = environ.get("SHORTENER_API3", "3ca9e6d453fa647f7dea5916f50519819919f62a")
SHORTENER_WEBSITE3 = environ.get("SHORTENER_WEBSITE3", "indiaearnx.com")
TWO_VERIFY_GAP = int(environ.get('TWO_VERIFY_GAP', "3600"))
THREE_VERIFY_GAP = int(environ.get('THREE_VERIFY_GAP', "3600"))

# languages search
LANGUAGES = ["hindi", "english", "telugu", "tamil", "kannada", "malayalam"]

auth_channel = environ.get('AUTH_CHANNEL', '-1002273359017')
AUTH_CHANNEL = int(auth_channel) if auth_channel and id_pattern.search(auth_channel) else None
SUPPORT_GROUP = int(environ.get('SUPPORT_GROUP', '-1001786924542'))

# bot settings
AUTO_FILTER = is_enabled('AUTO_FILTER', True)
PORT = os.environ.get('PORT', '8080')
MAX_BTN = int(environ.get('MAX_BTN', '8'))
AUTO_DELETE = is_enabled('AUTO_DELETE', True)
DELETE_TIME = int(environ.get('DELETE_TIME', 600))
IMDB = is_enabled('IMDB', False)
FILE_CAPTION = environ.get('FILE_CAPTION', f'{script.FILE_CAPTION}')
IMDB_TEMPLATE = environ.get('IMDB_TEMPLATE', f'{script.IMDB_TEMPLATE_TXT}')
LONG_IMDB_DESCRIPTION = is_enabled('LONG_IMDB_DESCRIPTION', False)
PROTECT_CONTENT = is_enabled('PROTECT_CONTENT', False)
SPELL_CHECK = is_enabled('SPELL_CHECK', True)
LINK_MODE = is_enabled('LINK_MODE', True)
PM_SEARCH = is_enabled('PM_SEARCH', True)
