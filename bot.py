# ================================================================
#  CineZone Telegram Bot
#  Features:
#   - Auto-add movies/series from channel uploads
#   - Duplicate detection & skip
#   - Web series episode grouping
#   - TMDB auto-fetch (poster, cast, rating, trailer)
#   - Force channel join check
#   - Shortlink verification (24hr)
#   - Subscriber check (skip verification)
#   - /get_movieid  → send file to user
#   - /search, /latest, /request commands
#   - Admin commands: /stats, /broadcast
#
#  Host FREE on Railway.app
#  Requirements: pip install pyTelegramBotAPI pymysql requests
# ================================================================

import telebot
import pymysql
import requests
import re
import os
import json
import hashlib
import time
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ── CONFIG ──────────────────────────────────────────────────────
BOT_TOKEN        = os.getenv('BOT_TOKEN',        '8532135669:AAH2uizTRL59WDwZpOGLDLxFTiFy3TAxJvA')
DB_HOST          = os.getenv('DB_HOST',          'srv1234.hostinger.com')
DB_NAME          = os.getenv('DB_NAME',          'u323305058_movie')
DB_USER          = os.getenv('DB_USER',          'u323305058_movie')
DB_PASS          = os.getenv('DB_PASS',          'Tekam7877')
TMDB_API_KEY     = os.getenv('TMDB_API_KEY',     '0a88081143284fa351c9deec774e1438')
PUBLIC_CHANNEL   = os.getenv('PUBLIC_CHANNEL',   '@jaatmovie88')   # announcement
STORAGE_CHANNEL  = os.getenv('STORAGE_CHANNEL',  '@jaatmovie88') # where you upload files
SITE_URL         = os.getenv('SITE_URL',         'https://movie.watchadearnmoney.online')
SHORTENER_URL    = os.getenv('SHORTENER_URL',    'indiaernx.com')  # your shortlink base URL
ADMIN_IDS        = [int(x) for x in os.getenv('ADMIN_IDS', '5469498838').split(',')]
VERIFY_HOURS     = int(os.getenv('VERIFY_HOURS', '24'))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# ── DATABASE ─────────────────────────────────────────────────────
def get_db():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS,
        database=DB_NAME, charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

def db_query(sql, params=(), fetch='all'):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch == 'one':  return cur.fetchone()
            if fetch == 'val':  return cur.fetchone()
            if fetch == 'id':   return cur.lastrowid
            return cur.fetchall()
    finally:
        conn.close()

def db_exec(sql, params=()):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()

# ── TMDB HELPER ──────────────────────────────────────────────────
TMDB_BASE  = 'https://api.themoviedb.org/3'
TMDB_IMG   = 'https://image.tmdb.org/t/p/w500'
TMDB_IMGBG = 'https://image.tmdb.org/t/p/original'

def tmdb_search(query, is_series=False):
    """Search TMDB for movie or TV series."""
    endpoint = 'tv' if is_series else 'movie'
    try:
        r = requests.get(
            f'{TMDB_BASE}/search/{endpoint}',
            params={'api_key': TMDB_API_KEY, 'query': query, 'language': 'en-US'},
            timeout=10
        )
        data = r.json()
        results = data.get('results', [])
        return results[0] if results else None
    except Exception as e:
        print(f'TMDB search error: {e}')
        return None

def tmdb_details(tmdb_id, is_series=False):
    """Get full details including cast, trailer, genres."""
    endpoint = 'tv' if is_series else 'movie'
    try:
        r = requests.get(
            f'{TMDB_BASE}/{endpoint}/{tmdb_id}',
            params={'api_key': TMDB_API_KEY, 'append_to_response': 'credits,videos', 'language': 'en-US'},
            timeout=10
        )
        return r.json()
    except Exception as e:
        print(f'TMDB details error: {e}')
        return {}

def tmdb_by_imdb(imdb_id):
    """Find TMDB entry by IMDb ID."""
    try:
        r = requests.get(
            f'{TMDB_BASE}/find/{imdb_id}',
            params={'api_key': TMDB_API_KEY, 'external_source': 'imdb_id'},
            timeout=10
        )
        data = r.json()
        results = data.get('movie_results', []) or data.get('tv_results', [])
        return results[0] if results else None
    except:
        return None

def extract_tmdb_info(data, is_series=False):
    """Extract clean info dict from TMDB response."""
    credits = data.get('credits', {})
    cast    = [c['name'] for c in credits.get('cast', [])[:10]]
    director = ''
    for c in credits.get('crew', []):
        if c.get('job') == 'Director':
            director = c['name']
            break

    trailer = ''
    for v in data.get('videos', {}).get('results', []):
        if v.get('type') == 'Trailer' and v.get('site') == 'YouTube':
            trailer = f"https://www.youtube.com/watch?v={v['key']}"
            break

    genres  = ', '.join([g['name'] for g in data.get('genres', [])])
    runtime = data.get('runtime') or 0

    # TV series fields
    if is_series:
        title   = data.get('name', '')
        year    = str(data.get('first_air_date', ''))[:4]
        seasons = data.get('number_of_seasons', 1)
        eps     = data.get('number_of_episodes', 0)
        dur     = f'{seasons} Season{"s" if seasons>1 else ""}, {eps} Episodes'
    else:
        title  = data.get('title', '')
        year   = str(data.get('release_date', ''))[:4]
        dur    = f'{runtime//60}h {runtime%60}m' if runtime else ''
        seasons = None

    return {
        'title':          title,
        'original_title': data.get('original_title') or data.get('original_name') or title,
        'year':           year,
        'duration':       dur,
        'description':    data.get('overview', ''),
        'imdb_id':        data.get('imdb_id', ''),
        'imdb_rating':    data.get('vote_average', 0),
        'genre':          genres,
        'director':       director,
        'cast_list':      ', '.join(cast),
        'language':       (data.get('original_language') or '').upper(),
        'country':        ', '.join([c['name'] for c in data.get('production_countries', [])]),
        'poster_url':     (TMDB_IMG   + data['poster_path'])   if data.get('poster_path')   else '',
        'backdrop_url':   (TMDB_IMGBG + data['backdrop_path']) if data.get('backdrop_path') else '',
        'trailer_url':    trailer,
        'seasons':        seasons,
        'tmdb_id':        data.get('id'),
    }

# ── CAPTION PARSER ───────────────────────────────────────────────
def parse_caption(caption):
    """
    Parse upload caption to extract movie info.

    Supported formats:
      Stree 2 (2024) Hindi 4K
      Pushpa 2 | Hindi | 4K | 2.5GB
      S01E01 | Mirzapur S1 | Hindi | 720p | 1.2GB
      tt12345678 | Hindi | 4K
      [Series] Mirzapur S02E01 Hindi 1080p
    """
    info = {
        'raw':        caption.strip(),
        'title':      '',
        'year':       '',
        'language':   'Hindi',
        'quality':    'HD',
        'file_size':  '',
        'is_series':  False,
        'season':     None,
        'episode':    None,
        'imdb_id':    '',
        'format':     'MKV',
    }

    text = caption.strip()

    # Detect series tag
    if re.search(r'\[series\]|\[web.?series\]', text, re.I):
        info['is_series'] = True
        text = re.sub(r'\[.*?\]', '', text).strip()

    # IMDb ID
    imdb_match = re.search(r'tt\d{7,8}', text)
    if imdb_match:
        info['imdb_id'] = imdb_match.group()
        text = text.replace(info['imdb_id'], '').strip()

    # Season/Episode  S01E01 or S1E1
    se_match = re.search(r'[Ss](\d{1,2})[Ee](\d{1,3})', text)
    if se_match:
        info['is_series'] = True
        info['season']    = int(se_match.group(1))
        info['episode']   = int(se_match.group(2))
        text = text.replace(se_match.group(), '').strip()

    # Season only  S01 / Season 2
    s_match = re.search(r'[Ss]eason\s*(\d+)|[Ss](\d{1,2})\b', text)
    if s_match and not se_match:
        info['is_series'] = True
        info['season']    = int(s_match.group(1) or s_match.group(2))
        text = re.sub(r'[Ss]eason\s*\d+|[Ss]\d{1,2}\b', '', text).strip()

    # Quality
    q_match = re.search(r'4K|2160p|1080p|720p|480p|360p|HDRip|WEB-DL|WEBRip|BluRay|CAM|HDTV', text, re.I)
    if q_match:
        q = q_match.group().upper()
        info['quality'] = '4K' if q in ('4K','2160P') else q_match.group()
        text = text.replace(q_match.group(), '').strip()

    # File size  e.g. 2.5GB  1.2 GB  800MB
    size_match = re.search(r'(\d+\.?\d*)\s*(GB|MB)', text, re.I)
    if size_match:
        info['file_size'] = size_match.group().strip()
        text = text.replace(size_match.group(), '').strip()

    # Year  (2024) or 2024
    year_match = re.search(r'\(?(\d{4})\)?', text)
    if year_match:
        yr = int(year_match.group(1))
        if 1950 <= yr <= 2030:
            info['year'] = str(yr)
            text = text.replace(year_match.group(), '').strip()

    # Language
    lang_match = re.search(
        r'\b(Hindi|English|Tamil|Telugu|Malayalam|Kannada|Bengali|Punjabi|Marathi|Dual Audio|Multi)\b',
        text, re.I
    )
    if lang_match:
        info['language'] = lang_match.group()
        text = text.replace(lang_match.group(), '').strip()

    # Format
    fmt_match = re.search(r'\b(MKV|MP4|AVI)\b', text, re.I)
    if fmt_match:
        info['format'] = fmt_match.group().upper()
        text = text.replace(fmt_match.group(), '').strip()

    # Clean up remaining text = title
    title = re.sub(r'[|\-_]+', ' ', text)
    title = re.sub(r'\s+', ' ', title).strip()
    title = title.strip('|-_ ')
    info['title'] = title

    return info

# ── SLUG HELPER ──────────────────────────────────────────────────
def make_slug(text):
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')

# ── DUPLICATE CHECK ──────────────────────────────────────────────
def is_duplicate_file(tg_file_id, tg_file_unique_id=None):
    """Check if this exact file is already in DB."""
    row = db_query(
        "SELECT id FROM movie_files WHERE tg_file_id = %s LIMIT 1",
        (tg_file_id,), fetch='one'
    )
    return row is not None

def is_duplicate_movie(title, year):
    """Check if movie with same title+year exists."""
    slug = make_slug(f"{title}-{year}")
    row  = db_query(
        "SELECT id, slug FROM movies WHERE slug = %s OR (LOWER(title) = LOWER(%s) AND year = %s) LIMIT 1",
        (slug, title, year), fetch='one'
    )
    return row

def is_duplicate_episode(series_id, season, episode):
    """Check if this specific episode already exists."""
    row = db_query(
        "SELECT id FROM series_episodes WHERE series_id=%s AND season=%s AND episode=%s LIMIT 1",
        (series_id, season, episode), fetch='one'
    )
    return row is not None

# ── SAVE MOVIE TO DB ─────────────────────────────────────────────
def save_movie(info, tmdb_info, tg_file_id, tg_message_id, category='Bollywood'):
    """Save movie + file to database. Returns (movie_id, is_new)."""
    title = tmdb_info.get('title') or info['title']
    year  = tmdb_info.get('year')  or info['year'] or str(datetime.now().year)

    # Check duplicate movie
    existing = is_duplicate_movie(title, year)
    if existing:
        movie_id = existing['id']
        is_new   = False
    else:
        slug = make_slug(f"{title}-{year}")
        # Ensure unique slug
        count = db_query("SELECT COUNT(*) as c FROM movies WHERE slug LIKE %s", (slug+'%',), fetch='one')
        if count and count['c'] > 0:
            slug = f"{slug}-{int(time.time())}"

        movie_id = db_exec("""
            INSERT INTO movies
                (slug, title, original_title, year, duration, category, language,
                 genre, director, cast_list, country, description,
                 imdb_id, imdb_rating, poster_url, backdrop_url, trailer_url,
                 status, featured)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',0)
        """, (
            slug,
            title,
            tmdb_info.get('original_title', title),
            year,
            tmdb_info.get('duration', ''),
            category,
            info['language'],
            tmdb_info.get('genre', ''),
            tmdb_info.get('director', ''),
            tmdb_info.get('cast_list', ''),
            tmdb_info.get('country', 'India'),
            tmdb_info.get('description', ''),
            tmdb_info.get('imdb_id', ''),
            tmdb_info.get('imdb_rating') or None,
            tmdb_info.get('poster_url', ''),
            tmdb_info.get('backdrop_url', ''),
            tmdb_info.get('trailer_url', ''),
        ))
        is_new = True

    # Add file if not duplicate
    if not is_duplicate_file(tg_file_id):
        db_exec("""
            INSERT INTO movie_files
                (movie_id, quality, format, file_size, language, tg_file_id, tg_message_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            movie_id,
            info['quality'],
            info['format'],
            info['file_size'],
            info['language'],
            tg_file_id,
            tg_message_id,
        ))

    return movie_id, is_new

# ── SAVE SERIES ──────────────────────────────────────────────────
def save_series(info, tmdb_info, tg_file_id, tg_message_id):
    """Save web series + episode to database."""
    title = tmdb_info.get('title') or info['title']
    year  = tmdb_info.get('year')  or info['year'] or str(datetime.now().year)

    # Find or create series entry
    existing = db_query(
        "SELECT id FROM movies WHERE LOWER(title)=LOWER(%s) AND category='Web Series' LIMIT 1",
        (title,), fetch='one'
    )

    if existing:
        series_id = existing['id']
        is_new_series = False
    else:
        slug = make_slug(f"{title}-{year}-series")
        series_id = db_exec("""
            INSERT INTO movies
                (slug,title,original_title,year,duration,category,language,
                 genre,director,cast_list,country,description,
                 imdb_id,imdb_rating,poster_url,backdrop_url,trailer_url,
                 status,featured)
            VALUES (%s,%s,%s,%s,%s,'Web Series',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',0)
        """, (
            slug, title,
            tmdb_info.get('original_title', title),
            year,
            tmdb_info.get('duration', ''),
            info['language'],
            tmdb_info.get('genre', ''),
            tmdb_info.get('director', ''),
            tmdb_info.get('cast_list', ''),
            tmdb_info.get('country', 'India'),
            tmdb_info.get('description', ''),
            tmdb_info.get('imdb_id', ''),
            tmdb_info.get('imdb_rating') or None,
            tmdb_info.get('poster_url', ''),
            tmdb_info.get('backdrop_url', ''),
            tmdb_info.get('trailer_url', ''),
        ))
        is_new_series = True

    season  = info.get('season')  or 1
    episode = info.get('episode') or 1

    # Duplicate episode check
    if is_duplicate_episode(series_id, season, episode):
        return series_id, False, True  # series_id, is_new, is_duplicate

    # Save episode
    db_exec("""
        INSERT INTO series_episodes
            (series_id, season, episode, title, tg_file_id, tg_message_id,
             quality, format, file_size, language)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        series_id, season, episode,
        f"S{season:02d}E{episode:02d}",
        tg_file_id, tg_message_id,
        info['quality'], info['format'],
        info['file_size'], info['language'],
    ))

    # Update movie downloads counter with episode count
    db_exec(
        "UPDATE movies SET downloads=downloads+1 WHERE id=%s",
        (series_id,)
    )

    return series_id, is_new_series, False

# ── DETECT CATEGORY ──────────────────────────────────────────────
def detect_category(info, tmdb_info):
    lang    = (info.get('language') or '').lower()
    country = (tmdb_info.get('country') or '').lower()
    orig_lang = (tmdb_info.get('language') or '').lower()

    if info.get('is_series'):
        return 'Web Series'
    if orig_lang in ('ta', 'te', 'ml', 'kn'):
        return 'South Hindi' if 'hindi' in lang else 'South Hindi'
    if orig_lang == 'hi' or 'india' in country:
        return 'Bollywood'
    if 'hindi' in lang and orig_lang not in ('hi',):
        return 'Hindi Dubbed'
    if info['quality'] == '4K':
        return '4K Hub'
    return 'Hollywood'

# ── ANNOUNCE NEW MOVIE ───────────────────────────────────────────
def announce_movie(movie_id, info, tmdb_info, is_series=False, season=None, episode=None):
    """Post announcement to public channel."""
    title   = tmdb_info.get('title') or info['title']
    year    = tmdb_info.get('year')  or info['year']
    rating  = tmdb_info.get('imdb_rating') or ''
    poster  = tmdb_info.get('poster_url') or ''
    slug    = make_slug(f"{title}-{year}")
    url     = f"{SITE_URL}/movie/{slug}"

    if is_series:
        text = (
            f"📺 <b>NEW EPISODE ADDED!</b>\n\n"
            f"🎬 <b>{title}</b> S{season:02d}E{episode:02d}\n"
            f"📅 Year: {year}\n"
            f"🌐 Language: {info['language']}\n"
            f"📊 Quality: {info['quality']}\n"
            f"{'⭐ IMDb: ' + str(rating) + '/10' if rating else ''}\n\n"
            f"🔗 <a href='{url}'>Watch / Download</a>"
        )
    else:
        genre  = tmdb_info.get('genre', '')
        text = (
            f"🎬 <b>NEW MOVIE ADDED!</b>\n\n"
            f"📽️ <b>{title} ({year})</b>\n"
            f"{'⭐ IMDb: ' + str(rating) + '/10' if rating else ''}\n"
            f"{'🎭 ' + genre if genre else ''}\n"
            f"🌐 Language: {info['language']}\n"
            f"📊 Quality: {info['quality']}\n\n"
            f"🔗 <a href='{url}'>Watch / Download</a>\n\n"
            f"📢 Join: {PUBLIC_CHANNEL}"
        )

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('▶️ Watch / Download', url=url))
    kb.add(InlineKeyboardButton('📩 Get via Bot', url=f'https://t.me/{BOT_TOKEN.split(":")[0]}?start=get_{movie_id}'))

    try:
        if poster:
            bot.send_photo(PUBLIC_CHANNEL, poster, caption=text, reply_markup=kb)
        else:
            bot.send_message(PUBLIC_CHANNEL, text, reply_markup=kb)
    except Exception as e:
        print(f'Announce error: {e}')

# ================================================================
#  CHANNEL POST HANDLER — fires when file is uploaded to channel
# ================================================================
@bot.channel_post_handler(content_types=['document', 'video'])
def handle_channel_upload(message):
    """Main handler: auto-adds movie/series when file posted to storage channel."""

    # Only process from storage channel
    chat_username = getattr(message.chat, 'username', '')
    chat_id_str   = str(message.chat.id)
    storage_clean = STORAGE_CHANNEL.lstrip('@')

    if chat_username != storage_clean and chat_id_str != storage_channel_id():
        return

    # Get file info
    if message.document:
        file_obj       = message.document
        tg_file_id     = message.document.file_id
        tg_file_unique = message.document.file_unique_id
        file_name      = message.document.file_name or ''
    else:
        file_obj       = message.video
        tg_file_id     = message.video.file_id
        tg_file_unique = message.video.file_unique_id
        file_name      = ''

    caption = message.caption or file_name or ''

    # Skip if no caption/filename
    if not caption.strip():
        bot.send_message(
            ADMIN_IDS[0],
            f"⚠️ File uploaded without caption!\n"
            f"File ID: <code>{tg_file_id}</code>\n"
            f"Please reply with the movie name."
        )
        return

    # ── Duplicate file check ─────────────────────────────
    if is_duplicate_file(tg_file_id):
        bot.send_message(
            ADMIN_IDS[0],
            f"⏭️ <b>Duplicate Skipped</b>\n"
            f"File already exists in database.\n"
            f"Caption: <code>{caption[:100]}</code>"
        )
        return

    # ── Parse caption ────────────────────────────────────
    info = parse_caption(caption)

    if not info['title'] and not info['imdb_id']:
        bot.send_message(
            ADMIN_IDS[0],
            f"❓ Could not parse title from caption:\n<code>{caption}</code>\n\n"
            f"Use format: <code>Movie Name (Year) Language Quality</code>"
        )
        return

    # ── Fetch TMDB data ──────────────────────────────────
    tmdb_raw  = None
    tmdb_info = {}

    if info['imdb_id']:
        tmdb_raw = tmdb_by_imdb(info['imdb_id'])
        if tmdb_raw:
            full = tmdb_details(tmdb_raw['id'], info['is_series'])
            tmdb_info = extract_tmdb_info(full, info['is_series'])
    
    if not tmdb_raw and info['title']:
        tmdb_raw = tmdb_search(info['title'], info['is_series'])
        if tmdb_raw:
            full = tmdb_details(tmdb_raw['id'], info['is_series'])
            tmdb_info = extract_tmdb_info(full, info['is_series'])

    if not tmdb_info:
        # Use caption info as fallback
        tmdb_info = {
            'title':    info['title'],
            'year':     info['year'],
            'language': info['language'],
        }

    # ── Save to database ─────────────────────────────────
    try:
        if info['is_series']:
            series_id, is_new, is_dup_ep = save_series(
                info, tmdb_info, tg_file_id, message.message_id
            )
            if is_dup_ep:
                bot.send_message(
                    ADMIN_IDS[0],
                    f"⏭️ <b>Duplicate Episode Skipped</b>\n"
                    f"S{info['season']:02d}E{info['episode']:02d} already exists for "
                    f"<b>{tmdb_info.get('title', info['title'])}</b>"
                )
                return

            title  = tmdb_info.get('title') or info['title']
            s, e   = info.get('season',1), info.get('episode',1)
            status_msg = (
                f"{'✅ New Series Created' if is_new else '📺 Episode Added'}\n\n"
                f"📺 <b>{title}</b>\n"
                f"Episode: S{s:02d}E{e:02d}\n"
                f"Quality: {info['quality']} | {info['language']}\n"
                f"File ID: <code>{tg_file_id}</code>"
            )
            bot.send_message(ADMIN_IDS[0], status_msg)

            if is_new:
                announce_movie(series_id, info, tmdb_info, True, s, e)
            else:
                # Just announce episode
                announce_movie(series_id, info, tmdb_info, True, s, e)

        else:
            category = detect_category(info, tmdb_info)
            movie_id, is_new = save_movie(
                info, tmdb_info, tg_file_id, message.message_id, category
            )
            title = tmdb_info.get('title') or info['title']
            slug  = make_slug(f"{title}-{tmdb_info.get('year', info['year'])}")

            status_msg = (
                f"{'✅ New Movie Added' if is_new else '📥 Quality Added to Existing'}\n\n"
                f"🎬 <b>{title}</b> ({tmdb_info.get('year', info['year'])})\n"
                f"Category: {category}\n"
                f"Quality: {info['quality']} | {info['language']}\n"
                f"{'⭐ IMDb: ' + str(tmdb_info.get('imdb_rating','')) if tmdb_info.get('imdb_rating') else ''}\n"
                f"🔗 {SITE_URL}/movie/{slug}\n"
                f"File ID: <code>{tg_file_id}</code>"
            )
            bot.send_message(ADMIN_IDS[0], status_msg)

            if is_new:
                announce_movie(movie_id, info, tmdb_info)

    except Exception as e:
        bot.send_message(ADMIN_IDS[0], f"❌ Error saving: {e}\nCaption: {caption[:100]}")
        print(f'Save error: {e}')

def storage_channel_id():
    try:
        chat = bot.get_chat(STORAGE_CHANNEL)
        return str(chat.id)
    except:
        return ''

# ================================================================
#  USER COMMANDS
# ================================================================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    name    = message.from_user.first_name or 'there'

    # Save/update user
    try:
        db_exec("""
            INSERT INTO telegram_users (telegram_id, username, first_name)
            VALUES (%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                username=VALUES(username), first_name=VALUES(first_name),
                last_seen=NOW()
        """, (user_id, message.from_user.username or '', name))
    except: pass

    # Check for /start get_MOVIEID
    param = message.text.split(' ', 1)
    if len(param) > 1 and param[1].startswith('get_'):
        movie_id = param[1][4:]
        send_movie_file(message, movie_id)
        return

    # Check channel membership
    if not is_channel_member(user_id):
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(f'📢 Join {PUBLIC_CHANNEL}', url=f'https://t.me/{PUBLIC_CHANNEL.lstrip("@")}'))
        kb.add(InlineKeyboardButton('✅ I Joined', callback_data='check_join'))
        bot.send_message(
            user_id,
            f"👋 Welcome to <b>CineZone Bot</b>, {name}!\n\n"
            f"📢 Please join our channel first to use the bot:\n{PUBLIC_CHANNEL}\n\n"
            f"After joining, tap <b>✅ I Joined</b>",
            reply_markup=kb
        )
        return

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('🎬 Latest Movies', callback_data='latest'),
        InlineKeyboardButton('🔍 Search', callback_data='search_prompt'),
        InlineKeyboardButton('📺 Web Series', callback_data='series'),
        InlineKeyboardButton('⭐ Subscribe', url=f'{SITE_URL}/#subscribe'),
        InlineKeyboardButton('🌐 Website', url=SITE_URL),
    )
    bot.send_message(
        user_id,
        f"🎬 <b>Welcome to CineZone Bot!</b>\n\n"
        f"Hi {name}! I can send you movies directly.\n\n"
        f"📥 <b>How to get a movie:</b>\n"
        f"1. Go to {SITE_URL}\n"
        f"2. Find your movie\n"
        f"3. Click 'Get via Telegram Bot'\n"
        f"4. I'll send it here!\n\n"
        f"Or use /search to find movies here.",
        reply_markup=kb
    )

@bot.message_handler(commands=['get'])
def cmd_get(message):
    parts = message.text.split(' ', 1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /get movie-slug\nExample: /get stree-2-2024")
        return
    send_movie_file(message, parts[1].strip())

@bot.message_handler(commands=['search'])
def cmd_search(message):
    parts = message.text.split(' ', 1)
    if len(parts) < 2:
        bot.reply_to(message, "🔍 Usage: /search Movie Name\nExample: /search Stree 2")
        return
    query = parts[1].strip()
    do_search(message, query)

@bot.message_handler(commands=['latest'])
def cmd_latest(message):
    movies = db_query("""
        SELECT id, slug, title, year, category, imdb_rating,
               GROUP_CONCAT(DISTINCT mf.quality SEPARATOR ', ') as qualities
        FROM movies m
        LEFT JOIN movie_files mf ON mf.movie_id=m.id
        WHERE m.status='active'
        GROUP BY m.id
        ORDER BY m.created_at DESC
        LIMIT 8
    """)
    if not movies:
        bot.reply_to(message, "No movies yet!")
        return

    text = "🔥 <b>Latest Releases:</b>\n\n"
    kb   = InlineKeyboardMarkup(row_width=2)
    for m in movies:
        rating = f"⭐{m['imdb_rating']}" if m['imdb_rating'] else ''
        text  += f"🎬 <b>{m['title']}</b> ({m['year']}) {rating}\n"
        kb.add(InlineKeyboardButton(
            f"📥 {m['title'][:25]}",
            callback_data=f"get_{m['id']}"
        ))
    bot.send_message(message.chat.id, text, reply_markup=kb)

@bot.message_handler(commands=['request'])
def cmd_request(message):
    parts = message.text.split(' ', 1)
    if len(parts) < 2:
        bot.reply_to(message, "📝 Usage: /request Movie Name\nExample: /request Leo Tamil")
        return

    title = parts[1].strip()
    try:
        db_exec(
            "INSERT INTO movie_requests (title, votes) VALUES (%s, 1) "
            "ON DUPLICATE KEY UPDATE votes=votes+1",
            (title,)
        )
        bot.reply_to(message, f"✅ Request submitted: <b>{title}</b>\nWe'll add it soon!")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(commands=['myplan'])
def cmd_myplan(message):
    tg_id = message.from_user.id
    user  = db_query(
        "SELECT plan, sub_expires FROM users WHERE telegram_id=%s LIMIT 1",
        (tg_id,), fetch='one'
    )
    if not user or user['plan'] == 'free':
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton('⭐ Subscribe Now', url=f'{SITE_URL}/#subscribe'))
        bot.reply_to(
            message,
            "📋 Your current plan: <b>Free</b>\n\n"
            "Subscribe to skip verification and get priority access!",
            reply_markup=kb
        )
    else:
        exp = user['sub_expires'] or 'Lifetime'
        bot.reply_to(
            message,
            f"⭐ Your plan: <b>{user['plan'].title()}</b>\n"
            f"Expires: {exp}\n\n"
            f"Thank you for subscribing! 🎉"
        )

# ── ADMIN COMMANDS ───────────────────────────────────────────────
@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    total_movies = db_query("SELECT COUNT(*) as c FROM movies WHERE status='active'", fetch='one')['c']
    total_subs   = db_query("SELECT COUNT(*) as c FROM users WHERE plan!='free'",     fetch='one')['c']
    total_tg     = db_query("SELECT COUNT(*) as c FROM telegram_users",               fetch='one')['c']
    today_dl     = db_query("SELECT COALESCE(SUM(downloads),0) as c FROM visitor_stats WHERE stat_date=CURDATE()", fetch='one')['c']

    bot.reply_to(
        message,
        f"📊 <b>CineZone Stats</b>\n\n"
        f"🎬 Movies: {total_movies}\n"
        f"⭐ Subscribers: {total_subs}\n"
        f"🤖 Bot Users: {total_tg}\n"
        f"📥 Downloads Today: {today_dl}\n"
        f"\n🔗 Admin: {SITE_URL}/admin.html"
    )

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split(' ', 1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /broadcast Your message here")
        return

    text  = parts[1]
    users = db_query("SELECT telegram_id FROM telegram_users WHERE telegram_id IS NOT NULL")
    sent  = 0
    for u in users:
        try:
            bot.send_message(u['telegram_id'], f"📢 <b>CineZone Update:</b>\n\n{text}")
            sent += 1
            time.sleep(0.05)  # avoid flood
        except: pass
    bot.reply_to(message, f"✅ Broadcast sent to {sent} users.")

# ── CALLBACK HANDLER ─────────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    uid  = call.from_user.id
    data = call.data

    if data == 'check_join':
        if is_channel_member(uid):
            bot.answer_callback_query(call.id, "✅ Verified!")
            bot.delete_message(uid, call.message.message_id)
            cmd_start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Please join the channel first!", show_alert=True)

    elif data.startswith('get_'):
        movie_id = data[4:]
        send_movie_file(call.message, movie_id, uid)
        bot.answer_callback_query(call.id)

    elif data == 'latest':
        cmd_latest(call.message)
        bot.answer_callback_query(call.id)

    elif data == 'search_prompt':
        bot.answer_callback_query(call.id)
        bot.send_message(uid, "🔍 Send me a movie name to search:")
        bot.register_next_step_handler_by_chat_id(uid, lambda m: do_search(m, m.text))

# ── SEND FILE TO USER ────────────────────────────────────────────
def send_movie_file(message, movie_id_or_slug, override_uid=None):
    uid = override_uid or message.chat.id

    # Check channel membership
    if not is_channel_member(uid):
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(f'📢 Join Channel', url=f'https://t.me/{PUBLIC_CHANNEL.lstrip("@")}'))
        bot.send_message(uid, f"📢 Please join {PUBLIC_CHANNEL} first!", reply_markup=kb)
        return

    # Find movie
    try:
        mid = int(movie_id_or_slug)
        movie = db_query("SELECT * FROM movies WHERE id=%s AND status='active' LIMIT 1", (mid,), fetch='one')
    except:
        slug  = movie_id_or_slug
        movie = db_query("SELECT * FROM movies WHERE slug=%s AND status='active' LIMIT 1", (slug,), fetch='one')

    if not movie:
        bot.send_message(uid, "❌ Movie not found. Check the website for correct link.")
        return

    # Check if subscriber
    tg_user  = db_query("SELECT * FROM users WHERE telegram_id=%s LIMIT 1", (uid,), fetch='one')
    is_sub   = tg_user and tg_user.get('plan','free') != 'free'
    verified = is_user_verified(uid)

    if not is_sub and not verified:
        # Send verification link
        short_url = build_verify_link(uid, movie['id'])
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton('🔓 Verify Once (Free)', url=short_url))
        kb.add(InlineKeyboardButton('⭐ Subscribe to Skip Always', url=f'{SITE_URL}/#subscribe'))
        bot.send_message(
            uid,
            f"🔐 <b>Quick Verification Required</b>\n\n"
            f"To get <b>{movie['title']}</b>, complete a quick one-time verification.\n"
            f"✅ Valid for {VERIFY_HOURS} hours after completion!\n\n"
            f"⭐ <b>Tip:</b> Subscribe to skip this forever.",
            reply_markup=kb
        )
        return

    # Get files
    files = db_query(
        "SELECT * FROM movie_files WHERE movie_id=%s AND is_active=1 ORDER BY quality",
        (movie['id'],)
    )

    if not files:
        bot.send_message(uid, f"⚠️ No download files available for <b>{movie['title']}</b> yet.")
        return

    # If single file, send directly
    if len(files) == 1:
        f = files[0]
        try:
            bot.send_document(uid, f['tg_file_id'],
                caption=f"🎬 <b>{movie['title']}</b> ({movie['year']})\n"
                        f"📊 {f['quality']} | {f['language']} | {f['file_size']}\n"
                        f"🔗 {SITE_URL}/movie/{movie['slug']}"
            )
            log_download(movie['id'], f['id'], uid, 'bot', f['quality'])
        except Exception as e:
            bot.send_message(uid, f"❌ Error sending file: {e}")
        return

    # Multiple qualities — show selection
    kb = InlineKeyboardMarkup()
    for f in files:
        size = f['file_size'] or '?'
        kb.add(InlineKeyboardButton(
            f"📥 {f['quality']} | {f['language']} | {size}",
            callback_data=f"file_{f['id']}_{movie['id']}"
        ))
    bot.send_message(
        uid,
        f"🎬 <b>{movie['title']}</b> ({movie['year']})\n"
        f"{'⭐ IMDb: ' + str(movie['imdb_rating']) if movie.get('imdb_rating') else ''}\n\n"
        f"Choose quality:",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith('file_'))
def send_file_by_id(call):
    parts   = call.data.split('_')
    file_id = int(parts[1])
    movie_id= int(parts[2])

    f = db_query("SELECT * FROM movie_files WHERE id=%s LIMIT 1", (file_id,), fetch='one')
    m = db_query("SELECT * FROM movies WHERE id=%s LIMIT 1", (movie_id,), fetch='one')

    if not f or not m:
        bot.answer_callback_query(call.id, "File not found!")
        return

    bot.answer_callback_query(call.id, "📤 Sending...")
    try:
        bot.send_document(
            call.from_user.id,
            f['tg_file_id'],
            caption=f"🎬 <b>{m['title']}</b> ({m['year']})\n"
                    f"📊 {f['quality']} | {f['language']} | {f['file_size']}\n"
                    f"🔗 {SITE_URL}/movie/{m['slug']}"
        )
        log_download(movie_id, file_id, call.from_user.id, 'bot', f['quality'])
    except Exception as e:
        bot.send_message(call.from_user.id, f"❌ Error: {e}")

# ── TEXT SEARCH ──────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.chat.type == 'private' and not m.text.startswith('/'))
def handle_text(message):
    do_search(message, message.text)

def do_search(message, query):
    query = query.strip()
    if len(query) < 2:
        bot.reply_to(message, "Please enter at least 2 characters.")
        return

    movies = db_query("""
        SELECT id, slug, title, year, category, imdb_rating,
               GROUP_CONCAT(DISTINCT mf.quality SEPARATOR ', ') as qualities
        FROM movies m
        LEFT JOIN movie_files mf ON mf.movie_id=m.id
        WHERE m.status='active' AND (m.title LIKE %s OR m.description LIKE %s)
        GROUP BY m.id
        ORDER BY m.downloads DESC
        LIMIT 6
    """, (f'%{query}%', f'%{query}%'))

    if not movies:
        bot.reply_to(message, f"❌ No results for: <b>{query}</b>\n\nTry /request {query} to request it!")
        return

    text = f"🔍 Results for <b>{query}</b>:\n\n"
    kb   = InlineKeyboardMarkup(row_width=1)
    for m in movies:
        r   = f" ⭐{m['imdb_rating']}" if m.get('imdb_rating') else ''
        q   = f" [{m['qualities']}]" if m.get('qualities') else ''
        text += f"🎬 <b>{m['title']}</b> ({m['year']}){r}{q}\n"
        kb.add(InlineKeyboardButton(
            f"📥 Get: {m['title'][:30]}",
            callback_data=f"get_{m['id']}"
        ))
    bot.send_message(message.chat.id, text, reply_markup=kb)

# ── HELPERS ──────────────────────────────────────────────────────
def is_channel_member(user_id):
    try:
        member = bot.get_chat_member(PUBLIC_CHANNEL, user_id)
        return member.status not in ('left', 'kicked', 'banned')
    except:
        return True  # if can't check, allow

def is_user_verified(user_id):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row = db_query(
        "SELECT id FROM verifications WHERE ip=%s AND expires_at>%s LIMIT 1",
        (str(user_id), now), fetch='one'
    )
    return row is not None

def build_verify_link(user_id, movie_id):
    if not SHORTENER_URL:
        return f"{SITE_URL}/verify?user={user_id}&movie={movie_id}"
    callback = f"{SITE_URL}/api/verify.php?action=callback&token={user_id}&back={SITE_URL}"
    return f"{SHORTENER_URL}/{callback}"

def log_download(movie_id, file_id, user_id, via='bot', quality=''):
    try:
        db_exec(
            "UPDATE movies SET downloads=downloads+1 WHERE id=%s", (movie_id,)
        )
        db_exec(
            "UPDATE movie_files SET download_count=download_count+1 WHERE id=%s", (file_id,)
        )
        db_exec(
            "INSERT INTO download_logs (movie_id,file_id,ip,via,quality) VALUES (%s,%s,%s,%s,%s)",
            (movie_id, file_id, str(user_id), via, quality)
        )
        today = datetime.now().strftime('%Y-%m-%d')
        db_exec(
            "INSERT INTO visitor_stats (stat_date,downloads) VALUES (%s,1) "
            "ON DUPLICATE KEY UPDATE downloads=downloads+1",
            (today,)
        )
    except Exception as e:
        print(f'Log download error: {e}')

# ================================================================
#  MAIN
# ================================================================
if __name__ == '__main__':
    print('🎬 CineZone Bot starting...')
    print(f'   Public channel : {PUBLIC_CHANNEL}')
    print(f'   Storage channel: {STORAGE_CHANNEL}')
    print(f'   Site URL       : {SITE_URL}')
    print(f'   Admin IDs      : {ADMIN_IDS}')
    print('✅ Bot is running!\n')

    # Create series_episodes table if not exists
    try:
        db_exec("""
            CREATE TABLE IF NOT EXISTS series_episodes (
                id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                series_id    INT UNSIGNED NOT NULL,
                season       SMALLINT UNSIGNED NOT NULL DEFAULT 1,
                episode      SMALLINT UNSIGNED NOT NULL DEFAULT 1,
                title        VARCHAR(200) DEFAULT NULL,
                tg_file_id   VARCHAR(200) NOT NULL,
                tg_message_id INT UNSIGNED DEFAULT NULL,
                quality      VARCHAR(20)  DEFAULT 'HD',
                format       VARCHAR(10)  DEFAULT 'MKV',
                file_size    VARCHAR(20)  DEFAULT NULL,
                language     VARCHAR(100) DEFAULT 'Hindi',
                download_count INT UNSIGNED NOT NULL DEFAULT 0,
                is_active    TINYINT(1)   NOT NULL DEFAULT 1,
                created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (series_id) REFERENCES movies(id) ON DELETE CASCADE,
                UNIQUE KEY unique_ep (series_id, season, episode),
                INDEX idx_series (series_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print('✅ series_episodes table ready')
    except Exception as e:
        print(f'Table note: {e}')

    bot.infinity_polling(timeout=30, long_polling_timeout=30)
