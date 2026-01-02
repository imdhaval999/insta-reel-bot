import telebot, os, json, time, shutil
from telebot import types
import instaloader
import http.cookiejar as cookielib
from keep_alive import keep_alive

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
keep_alive()

KEYS_FILE = "keys.json"
USERS_FILE = "users.json"

# ---------- helpers ----------
def load(f, d):
    if not os.path.exists(f):
        return d
    return json.load(open(f))

def save(f, d):
    json.dump(d, open(f, "w"), indent=2)

def welcome(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔑 My Key")
    bot.send_message(
        cid,
        "🔥 *Instagram Reel Downloader – Private Bot*\n\n"
        "🔐 Enter your key to start service\n"
        "💬 Buy key 👉 @imvrct",
        reply_markup=kb,
        parse_mode="Markdown"
    )

def key_status(uid):
    users = load(USERS_FILE, {})
    u = users.get(str(uid))
    if not u:
        return "none", None
    if u.get("deleted"):
        return "deleted", u
    if u.get("blocked"):
        return "blocked", u
    if time.time() > u["expire"]:
        return "expired", u
    return "active", u

def time_left(sec):
    if sec <= 0:
        return "Expired"
    m = sec // 60
    if m < 60:
        return f"{m} min"
    h = m // 60
    if h < 24:
        return f"{h} hrs"
    return f"{h//24} days"

# ---------- instagram ----------
L = instaloader.Instaloader(download_videos=True, save_metadata=False)
cj = cookielib.MozillaCookieJar("cookies.txt")
cj.load(ignore_discard=True, ignore_expires=True)
L.context._session.cookies = cj
DOWNLOAD_DIR = "downloads"

# ---------- start ----------
@bot.message_handler(commands=["start"])
def start(m):
    welcome(m.chat.id)

# ---------- my key ----------
@bot.message_handler(func=lambda m: m.text == "🔑 My Key")
def my_key(m):
    status, u = key_status(m.chat.id)

    if status == "none":
        bot.send_message(m.chat.id, "❌ No key found\n🔐 Enter your key")
        return

    if status == "active":
        msg = (
            f"🔑 *Your Key*\n\n"
            f"📌 Status: Active ✅\n"
            f"⏳ Time Left: {time_left(int(u['expire']-time.time()))}"
        )
    elif status == "blocked":
        msg = "🚫 *Your key is BLOCKED by admin*\n🔐 Enter new key"
    elif status == "deleted":
        msg = "🗑️ *Your key is DELETED by admin*\n🔐 Enter new key"
    else:
        msg = "⏰ *Your key is EXPIRED*\n🔐 Enter new key"

    bot.send_message(m.chat.id, msg, parse_mode="Markdown")

# ---------- key input ----------
@bot.message_handler(func=lambda m: m.text and m.text.startswith("imdhaval-"))
def check_key(m):
    bot.send_message(m.chat.id, "⏳ Checking your key…")

    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})

    if m.text not in keys:
        bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")
        return

    users[str(m.chat.id)] = {
        "key": m.text,
        "expire": time.time() + keys[m.text],
        "blocked": False,
        "deleted": False
    }
    del keys[m.text]
    save(KEYS_FILE, keys)
    save(USERS_FILE, users)

    bot.send_message(
        m.chat.id,
        "✅ *Successfully Logged In* 🎉\n"
        "👇 Send Instagram Reel link",
        parse_mode="Markdown"
    )

# ---------- reel ----------
@bot.message_handler(func=lambda m: "instagram.com/reel" in m.text)
def reel(m):
    status, _ = key_status(m.chat.id)

    if status != "active":
        if status == "blocked":
            bot.send_message(m.chat.id, "🚫 Your key is blocked\n🔐 Enter new key")
        elif status == "deleted":
            bot.send_message(m.chat.id, "🗑️ Your key is deleted\n🔐 Enter new key")
        elif status == "expired":
            bot.send_message(m.chat.id, "⏰ Key expired\n🔐 Enter new key")
        else:
            bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")
        return

    try:
        sc = m.text.split("/")[-2]
        msg = bot.send_message(m.chat.id, "⏳ Downloading reel…")

        post = instaloader.Post.from_shortcode(L.context, sc)

        if os.path.exists(DOWNLOAD_DIR):
            shutil.rmtree(DOWNLOAD_DIR)
        os.mkdir(DOWNLOAD_DIR)

        L.download_post(post, target=DOWNLOAD_DIR)

        for f in os.listdir(DOWNLOAD_DIR):
            if f.endswith(".mp4"):
                with open(os.path.join(DOWNLOAD_DIR, f), "rb") as v:
                    bot.send_video(m.chat.id, v, caption=post.caption or "")
                break

        shutil.rmtree(DOWNLOAD_DIR)
        bot.delete_message(m.chat.id, msg.message_id)

    except:
        if os.path.exists(DOWNLOAD_DIR):
            shutil.rmtree(DOWNLOAD_DIR)
        bot.send_message(m.chat.id, "❌ Failed to download reel")

# ---------- fallback ----------
@bot.message_handler(func=lambda m: True)
def fallback(m):
    if m.text != "/start":
        bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")

print("✅ User Bot FINAL & FIXED Running…")
bot.polling(non_stop=True)
