import telebot, os, json, time, re
from telebot import types
from keep_alive import keep_alive

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
keep_alive()

ADMIN_SECRET = "imdhaval"
KEY_PATTERN = re.compile(r"^imdhaval-\d+$")

KEYS_FILE = "keys.json"
USERS_FILE = "users.json"

admin_wait = set()
admin_live = set()
user_logged = set()

admin_gen = {}
admin_del = set()
admin_ext = {}

# ---------- helpers ----------
def load(f, d):
    if not os.path.exists(f): return d
    return json.load(open(f))

def save(f, d):
    json.dump(d, open(f, "w"), indent=2)

def welcome(uid):
    user_logged.discard(uid)
    bot.send_message(
        uid,
        "🔥 Instagram Reel Downloader – Private Bot\n\n"
        "🔐 Enter your key to start service\n"
        "💬 Buy key 👉 @imvrct"
    )

def logout_user(uid, msg):
    bot.send_message(uid, msg)
    welcome(uid)

# ---------- START ----------
@bot.message_handler(commands=["start"])
def start(m):
    admin_wait.discard(m.chat.id)
    admin_live.discard(m.chat.id)
    admin_del.discard(m.chat.id)
    admin_ext.pop(m.chat.id, None)
    welcome(m.chat.id)

# ---------- USER LOGIN ----------
@bot.message_handler(func=lambda m: m.text and KEY_PATTERN.match(m.text) and m.chat.id not in admin_live)
def user_key(m):
    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})

    key = m.text
    if key not in keys:
        bot.send_message(m.chat.id, "❌ Key not found")
        return

    k = keys[key]

    if k.get("blocked"):
        bot.send_message(m.chat.id, "🚫 Your key is blocked")
        return

    if k["type"] == "single" and k["used_by"]:
        bot.send_message(m.chat.id, "📵 Max device reached")
        return

    expire = time.time() + k["duration"]
    if expire <= time.time():
        bot.send_message(m.chat.id, "⏰ Your key is expired")
        return

    users[str(m.chat.id)] = {"key": key, "expire": expire}
    k["used_by"].append(m.chat.id)

    save(KEYS_FILE, keys)
    save(USERS_FILE, users)

    user_logged.add(m.chat.id)
    bot.send_message(m.chat.id, "✅ Login successful 🎉\nSend reel link 🎬")

# ---------- URL WITHOUT KEY ----------
@bot.message_handler(func=lambda m: m.text.startswith("http") and m.chat.id not in user_logged)
def url_without_key(m):
    bot.send_message(
        m.chat.id,
        "❌ Please purchase a key first\n💬 Contact @imvrct"
    )

# ---------- ADMIN ENTRY ----------
@bot.message_handler(func=lambda m: m.text == "Admin")
def admin_entry(m):
    admin_wait.add(m.chat.id)
    bot.send_message(m.chat.id, "👑 Welcome to Admin Panel\n🔐 Enter admin key")

@bot.message_handler(func=lambda m: m.chat.id in admin_wait)
def admin_key(m):
    if m.text == "/start":
        admin_wait.discard(m.chat.id)
        welcome(m.chat.id)
        return

    if m.text != ADMIN_SECRET:
        bot.send_message(m.chat.id, "❌ Invalid admin key\n🔁 Try again")
        return

    admin_wait.discard(m.chat.id)
    admin_live.add(m.chat.id)
    show_admin(m.chat.id)

# ---------- ADMIN PANEL ----------
def show_admin(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Generate Key", "📋 All Keys")
    kb.add("🗑️ Delete Key", "⏳ Extend Key")
    kb.add("🚪 Logout")
    bot.send_message(uid, "👑 Admin Panel", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🚪 Logout")
def admin_logout(m):
    admin_live.discard(m.chat.id)
    welcome(m.chat.id)

# ---------- GENERATE KEY ----------
@bot.message_handler(func=lambda m: m.text == "➕ Generate Key" and m.chat.id in admin_live)
def gen_type(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Single User", "Multi User", "⬅ Back")
    bot.send_message(m.chat.id, "Select key type", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_live and m.text in ["Single User","Multi User"])
def gen_dur(m):
    admin_gen[m.chat.id] = "single" if m.text=="Single User" else "multi"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 Min","1 Day","30 Day","⬅ Back")
    bot.send_message(m.chat.id, "Select duration", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_live and m.text in ["5 Min","1 Day","30 Day"])
def gen_key(m):
    d={"5 Min":300,"1 Day":86400,"30 Day":2592000}
    key="imdhaval-"+str(int(time.time()))
    keys=load(KEYS_FILE,{})
    keys[key]={
        "duration":d[m.text],
        "type":admin_gen[m.chat.id],
        "used_by":[],
        "blocked":False
    }
    save(KEYS_FILE,keys)
    bot.send_message(m.chat.id,f"✅ Key Generated\n🔑 `{key}`",parse_mode="Markdown")
    show_admin(m.chat.id)

# ---------- BACK ----------
@bot.message_handler(func=lambda m: m.text=="⬅ Back" and m.chat.id in admin_live)
def back(m):
    show_admin(m.chat.id)

# ---------- FALLBACK ----------
@bot.message_handler(func=lambda m: True)
def fallback(m):
    if m.text != "/start":
        bot.send_message(m.chat.id, "❌ Key not found")

print("✅ FINAL BOT RUNNING (LOCKED FLOW)")
bot.polling(non_stop=True)
