# ================= IMPORTS =================
import telebot, os, json, time, shutil, re
from telebot import types
import instaloader
import http.cookiejar as cookielib
from keep_alive import keep_alive

# ================= BASIC =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

bot = telebot.TeleBot(BOT_TOKEN)
keep_alive()

ADMIN_SECRET = "imdhaval"

KEYS_FILE  = "keys.json"
USERS_FILE = "users.json"

# ================= STATES =================
admin_wait = set()
admin_live = set()
user_logged = set()

admin_gen_state = {}
admin_del_wait = set()
admin_ext_wait = {}   # chat_id -> key or None

KEY_PATTERN = re.compile(r"^imdhaval-\w+")

# ================= HELPERS =================
def load(f, d):
    if not os.path.exists(f):
        return d
    return json.load(open(f))

def save(f, d):
    json.dump(d, open(f, "w"), indent=2)

def dur(sec):
    if sec <= 0:
        return "Expired"
    m = sec // 60
    if m < 60:
        return f"{m} Min"
    h = m // 60
    if h < 24:
        return f"{h} Hr"
    return f"{h//24} Day"

# ================= INSTAGRAM =================
L = instaloader.Instaloader(download_videos=True, save_metadata=False)
cj = cookielib.MozillaCookieJar("cookies.txt")
cj.load(ignore_discard=True, ignore_expires=True)
L.context._session.cookies = cj
DOWNLOAD_DIR = "downloads"

# ================= USER =================
def user_welcome(cid):
    user_logged.discard(cid)
    bot.send_message(
        cid,
        "🔥 Instagram Reel Downloader – Private Bot\n\n"
        "🔐 Enter your key to start service\n"
        "💬 Buy key 👉 @imvrct"
    )

@bot.message_handler(commands=["start"])
def start(m):
    admin_wait.discard(m.chat.id)
    admin_live.discard(m.chat.id)
    admin_del_wait.discard(m.chat.id)
    admin_ext_wait.pop(m.chat.id, None)
    user_welcome(m.chat.id)

# ---------- USER KEY LOGIN ----------
@bot.message_handler(func=lambda m: m.text and KEY_PATTERN.match(m.text) and m.chat.id not in admin_live)
def user_key(m):
    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})

    key = m.text

    if key not in keys:
        bot.send_message(m.chat.id, "❌ Key not found")
        return

    key_data = keys[key]

    if key_data.get("blocked"):
        bot.send_message(m.chat.id, "🚫 Your key is blocked")
        return

    if key_data["type"] == "single" and key_data["used_by"]:
        bot.send_message(m.chat.id, "📵 Max device reached")
        return

    expire = time.time() + key_data["duration"]
    if expire <= time.time():
        bot.send_message(m.chat.id, "⏰ Your key is expired")
        return

    users[str(m.chat.id)] = {
        "key": key,
        "expire": expire
    }

    key_data["used_by"].append(m.chat.id)
    save(KEYS_FILE, keys)
    save(USERS_FILE, users)

    user_logged.add(m.chat.id)
    bot.send_message(m.chat.id, "✅ Successfully Logged In 🎉\nSend reel link 🎬")

# ================= ADMIN =================
@bot.message_handler(func=lambda m: m.text == "Admin")
def admin_entry(m):
    admin_wait.add(m.chat.id)
    bot.send_message(m.chat.id, "👑 Welcome to Admin Panel\n🔐 Enter admin key")

@bot.message_handler(func=lambda m: m.chat.id in admin_wait)
def admin_key(m):
    if m.text == "/start":
        admin_wait.discard(m.chat.id)
        user_welcome(m.chat.id)
        return

    if m.text != ADMIN_SECRET:
        bot.send_message(m.chat.id, "❌ Key not found")
        return

    admin_wait.discard(m.chat.id)
    admin_live.add(m.chat.id)
    show_admin_panel(m.chat.id)

def show_admin_panel(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Generate Key")
    kb.add("📋 All Keys")
    kb.add("🗑️ Delete Key", "⏳ Extend Key")
    kb.add("🚪 Logout")
    bot.send_message(cid, "👑 Admin Panel", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🚪 Logout")
def admin_logout(m):
    admin_live.discard(m.chat.id)
    user_welcome(m.chat.id)

# ================= GENERATE KEY =================
@bot.message_handler(func=lambda m: m.text == "➕ Generate Key" and m.chat.id in admin_live)
def gen_type(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Single User", "Multi User")
    bot.send_message(m.chat.id, "Select key type", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_live and m.text in ["Single User", "Multi User"])
def gen_dur(m):
    admin_gen_state[m.chat.id] = "single" if m.text == "Single User" else "multi"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 Min", "1 Day", "30 Day")
    bot.send_message(m.chat.id, "Select duration", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_live and m.text in ["5 Min", "1 Day", "30 Day"])
def gen_key(m):
    dmap = {"5 Min": 300, "1 Day": 86400, "30 Day": 2592000}
    key = "imdhaval-" + str(int(time.time()))
    keys = load(KEYS_FILE, {})
    keys[key] = {
        "duration": dmap[m.text],
        "type": admin_gen_state[m.chat.id],
        "used_by": [],
        "extended": 0,
        "blocked": False
    }
    save(KEYS_FILE, keys)
    bot.send_message(m.chat.id, f"✅ Key Generated\n🔑 `{key}`", parse_mode="Markdown")
    show_admin_panel(m.chat.id)

# ================= ALL KEYS =================
@bot.message_handler(func=lambda m: m.text == "📋 All Keys" and m.chat.id in admin_live)
def all_keys(m):
    keys = load(KEYS_FILE, {})
    if not keys:
        bot.send_message(m.chat.id, "No keys found")
        return

    txt = ""
    for k, v in keys.items():
        status = "Used" if v["used_by"] else "Not Used"
        block = (
            f"🔑 `{k}`\n"
            f"👥 {v['type']}\n"
            f"📊 {status}\n"
            f"⏳ {dur(v['duration'])}\n"
            f"🔁 Extended ({v.get('extended',0)}x)\n\n"
        )
        if len(txt) + len(block) > 3800:
            bot.send_message(m.chat.id, txt, parse_mode="Markdown")
            txt = block
        else:
            txt += block

    if txt:
        bot.send_message(m.chat.id, txt, parse_mode="Markdown")

# ================= FALLBACK =================
@bot.message_handler(func=lambda m: True)
def fallback(m):
    if m.text != "/start":
        bot.send_message(m.chat.id, "❌ Key not found")

print("✅ FINAL STABLE BOT RUNNING")
bot.polling(non_stop=True)
