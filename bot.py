import telebot, os, json, time, shutil
from telebot import types
import instaloader
import http.cookiejar as cookielib
from keep_alive import keep_alive

# ================= BASIC =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
keep_alive()

ADMIN_SECRET = "imdhaval"

KEYS_FILE  = "keys.json"
USERS_FILE = "users.json"

admin_wait = set()
admin_live = set()
user_logged = set()

# ================= HELPERS =================
def load(f, d):
    if not os.path.exists(f):
        return d
    return json.load(open(f))

def save(f, d):
    json.dump(d, open(f, "w"), indent=2)

def duration_txt(sec):
    if sec <= 0: return "Expired"
    m = sec//60
    if m < 60: return f"{m} Min"
    h = m//60
    if h < 24: return f"{h} Hr"
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
    user_welcome(m.chat.id)

@bot.message_handler(func=lambda m: m.text and m.text.startswith("imdhaval-") and m.chat.id not in admin_live)
def user_key(m):
    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})

    if m.text not in keys:
        bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")
        return

    key_data = keys[m.text]

    if key_data["type"] == "single" and key_data["used_by"]:
        bot.send_message(m.chat.id, "🚫 This key already used")
        return

    expire = time.time() + key_data["duration"]
    users[str(m.chat.id)] = {
        "key": m.text,
        "expire": expire,
        "blocked": False,
        "deleted": False
    }

    key_data["used_by"].append(m.chat.id)
    save(KEYS_FILE, keys)
    save(USERS_FILE, users)

    user_logged.add(m.chat.id)
    bot.send_message(
        m.chat.id,
        "✅ Successfully Logged In 🎉\n"
        "👇 Send Instagram Reel link"
    )

# ================= ADMIN ENTRY =================
@bot.message_handler(func=lambda m: m.text == "Admin")
def admin_entry(m):
    admin_wait.add(m.chat.id)
    bot.send_message(
        m.chat.id,
        "👑 Welcome to Admin Panel\n🔐 Enter admin key"
    )

@bot.message_handler(func=lambda m: m.chat.id in admin_wait)
def admin_key(m):
    if m.text == "/start":
        admin_wait.discard(m.chat.id)
        user_welcome(m.chat.id)
        return
    if m.text != ADMIN_SECRET:
        bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")
        return
    admin_wait.discard(m.chat.id)
    admin_live.add(m.chat.id)
    show_admin_panel(m.chat.id)

# ================= ADMIN PANEL =================
def show_admin_panel(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Generate Key")
    kb.add("📂 Manage Keys")
    kb.add("🚪 Logout")
    bot.send_message(cid, "👑 Admin Panel", reply_markup=kb)

def admin_only(m):
    if m.chat.id not in admin_live:
        bot.send_message(m.chat.id, "🔐 Login as Admin")
        return False
    return True

@bot.message_handler(func=lambda m: m.text == "🚪 Logout")
def admin_logout(m):
    admin_live.discard(m.chat.id)
    user_welcome(m.chat.id)

# ================= GENERATE KEY =================
@bot.message_handler(func=lambda m: m.text == "➕ Generate Key")
def gen_menu(m):
    if not admin_only(m): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Single User", "Multi User")
    bot.send_message(m.chat.id, "Select key type", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_live and m.text in ["Single User","Multi User"])
def gen_duration(m):
    m.key_type = "single" if m.text == "Single User" else "multi"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 Min", "1 Day", "30 Day")
    bot.send_message(m.chat.id, "Select duration", reply_markup=kb)
    bot.register_next_step_handler(m, do_gen_key)

def do_gen_key(m):
    duration_map = {"5 Min":300,"1 Day":86400,"30 Day":2592000}
    key = "imdhaval-" + str(int(time.time()))
    keys = load(KEYS_FILE, {})
    keys[key] = {
        "duration": duration_map[m.text],
        "type": m.key_type,
        "used_by": []
    }
    save(KEYS_FILE, keys)
    bot.send_message(m.chat.id, f"✅ Key Generated\n🔑 `{key}`")

# ================= MANAGE KEYS =================
@bot.message_handler(func=lambda m: m.text == "📂 Manage Keys")
def manage_keys(m):
    if not admin_only(m): return
    keys = load(KEYS_FILE, {})
    if not keys:
        bot.send_message(m.chat.id, "No keys found")
        return

    msg = "📂 ALL KEYS\n\n"
    for k,v in keys.items():
        msg += (
            f"🔑 {k}\n"
            f"👥 Type: {v['type']}\n"
            f"⏳ {duration_txt(v['duration'])}\n"
            f"👤 Used: {len(v['used_by'])}\n"
            f"➡️ delete {k}\n"
            f"➡️ extend {k}\n\n"
        )
    bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text.startswith("delete "))
def del_key(m):
    if not admin_only(m): return
    key = m.text.replace("delete ","")
    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})
    if key in keys:
        del keys[key]
    for u in users.values():
        if u["key"] == key:
            u["deleted"] = True
    save(KEYS_FILE, keys)
    save(USERS_FILE, users)
    bot.send_message(m.chat.id, "🗑️ Key deleted")

@bot.message_handler(func=lambda m: m.text.startswith("extend "))
def extend_key(m):
    if not admin_only(m): return
    key = m.text.replace("extend ","")
    keys = load(KEYS_FILE, {})
    if key in keys:
        keys[key]["duration"] += 86400
        save(KEYS_FILE, keys)
        bot.send_message(m.chat.id, "⏳ Key extended by 1 Day")

# ================= FALLBACK =================
@bot.message_handler(func=lambda m: True)
def fallback(m):
    if m.text != "/start":
        bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")

print("✅ Single Bot with Advanced Admin Panel Running…")
bot.polling(non_stop=True)
