import asyncio
import random
import time
import sqlite3
import requests
from telethon import TelegramClient, events

# ================= CONFIG =================

API_ID = 35233651
API_HASH = "2a5cac9490ea716daa0f2bde1b805d41"
GEMINI_API_KEY = "AIzaSyB8re-iuuwNNOTIVh-1vcf0HeLFGqPq254"

OWNER_ID = 8405240051
SESSION = "ultra_ai"

INTRO_MESSAGE = "He is offline now, you can talk to me if you want, I am AI reply bot."
FALLBACK_MESSAGE = "I am AI reply bot Sorry I can't talk to you, he will reply when he is online."

OWNER_OFFLINE_DELAY = 300
MEMORY_LIMIT = 1000

# ================= TELEGRAM =================

client = TelegramClient(SESSION, API_ID, API_HASH)
last_owner_activity = time.time()

# ================= DATABASE =================

conn = sqlite3.connect("ai_memory.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memory(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
role TEXT,
message TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats(
user_id INTEGER,
messages INTEGER
)
""")

conn.commit()

# ================= MEMORY =================

def save_memory(uid, role, text):

    cursor.execute(
        "INSERT INTO memory (user_id,role,message) VALUES (?,?,?)",
        (uid, role, text)
    )

    conn.commit()

def get_memory(uid):

    cursor.execute(
        "SELECT role,message FROM memory WHERE user_id=? ORDER BY id DESC LIMIT 20",
        (uid,)
    )

    rows = cursor.fetchall()

    history = ""

    for r in reversed(rows):
        history += f"{r[0]}: {r[1]}\n"

    return history

# ================= STATS =================

def update_stats(uid):

    cursor.execute("SELECT messages FROM stats WHERE user_id=?", (uid,))
    row = cursor.fetchone()

    if row:
        cursor.execute(
            "UPDATE stats SET messages=? WHERE user_id=?",
            (row[0] + 1, uid)
        )
    else:
        cursor.execute(
            "INSERT INTO stats VALUES (?,?)",
            (uid, 1)
        )

    conn.commit()

# ================= EMOTION =================

def detect_emotion(text):

    t = text.lower()

    if "sad" in t or "কষ্ট" in t:
        return "sad"

    if "happy" in t or "ভালো" in t:
        return "happy"

    if "angry" in t or "রাগ" in t:
        return "angry"

    return "normal"

# ================= ANTI SPAM =================

user_last_msg = {}

def anti_spam(uid):

    now = time.time()

    if uid in user_last_msg:

        if now - user_last_msg[uid] < 2:
            return True

    user_last_msg[uid] = now

    return False

# ================= AI =================

def ai_reply(uid, text, emotion):

    history = get_memory(uid)

    prompt = f"""
You are chatting like a real friendly Telegram user.

Personality: Friendly, casual, human chat style.
Emotion detected: {emotion}

Conversation history:
{history}

User message:
{text}

Reply short and natural.
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    data = {
        "contents":[{"parts":[{"text": prompt}]}]
    }

    try:

        r = requests.post(url, json=data, timeout=60)

        reply = r.json()["candidates"][0]["content"]["parts"][0]["text"]

        return reply.strip()

    except:

        return None

# ================= HUMAN BEHAVIOUR =================

async def human_behavior(event, text):

    await client.send_read_acknowledge(event.chat_id)

    read_delay = random.randint(2,7)
    await asyncio.sleep(read_delay)

    typing_time = min(max(len(text)*0.1,3),15)

    try:
        async with client.action(event.chat_id,"typing"):
            await asyncio.sleep(typing_time)
    except:
        await asyncio.sleep(typing_time)

# ================= HANDLER =================

@client.on(events.NewMessage(incoming=True))
async def handler(event):

    global last_owner_activity

    sender = await event.get_sender()

    if sender.bot:
        return

    if not event.is_private:
        return

    uid = sender.id
    text = event.raw_text.strip()

    # owner online detect
    if uid == OWNER_ID:
        last_owner_activity = time.time()
        return

    # owner online
    if time.time() - last_owner_activity < OWNER_OFFLINE_DELAY:
        return

    # anti spam
    if anti_spam(uid):
        return

    # first message
    cursor.execute("SELECT * FROM memory WHERE user_id=? LIMIT 1",(uid,))
    first = cursor.fetchone()

    if not first:

        await asyncio.sleep(random.randint(2,4))

        await event.reply(INTRO_MESSAGE)

        save_memory(uid,"AI",INTRO_MESSAGE)

        return

    # emotion detect
    emotion = detect_emotion(text)

    save_memory(uid,"User",text)

    update_stats(uid)

    await human_behavior(event,text)

    reply = ai_reply(uid,text,emotion)

    if reply:

        save_memory(uid,"AI",reply)

        await event.reply(reply)

    else:

        await event.reply(FALLBACK_MESSAGE)

# ================= START =================

print("🤖 Ultra AI Telegram Userbot Running")

client.start()

client.run_until_disconnected()