import telebot, os, json, time, re
from telebot import types
from keep_alive import keep_alive

# ========== BASIC ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
keep_alive()

ADMIN_SECRET = "imdhaval"
KEY_PATTERN = re.compile(r"^imdhaval-\d+$")

KEYS_FILE  = "keys.json"
USERS_FILE = "users.json"

# ========== STATES ==========
admin_live = set()
admin_wait = set()

admin_del_wait = {}   # chat_id -> key or None
admin_ext_wait = {}   # chat_id -> key or None

user_logged = set()

# ========== HELPERS ==========
def load(f, d):
    if not os.path.exists(f): return d
    return json.load(open(f))

def save(f, d):
    json.dump(d, open(f, "w"), indent=2)

def is_key(t): 
    return bool(KEY_PATTERN.match(t))

def user_welcome(cid):
    user_logged.discard(cid)
    bot.send_message(
        cid,
        "🔥 Instagram Reel Downloader – Private Bot\n\n"
        "🔐 Enter your key to start service\n"
        "💬 Buy key 👉 @imvrct"
    )

def show_admin_panel(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📋 All Keys")
    kb.add("🗑️ Delete Key", "⏳ Extend Key")
    kb.add("🚪 Logout")
    bot.send_message(cid, "👑 Admin Panel", reply_markup=kb)

# ========== START ==========
@bot.message_handler(commands=["start"])
def start(m):
    admin_live.discard(m.chat.id)
    admin_wait.discard(m.chat.id)
    admin_del_wait.pop(m.chat.id, None)
    admin_ext_wait.pop(m.chat.id, None)
    user_welcome(m.chat.id)

# ========== USER LOGIN ==========
@bot.message_handler(
    func=lambda m:
    m.text and is_key(m.text)
    and m.chat.id not in admin_live
    and m.chat.id not in admin_del_wait
    and m.chat.id not in admin_ext_wait
)
def user_login(m):
    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})
    k = keys.get(m.text)

    if not k:
        bot.send_message(m.chat.id, "❌ Key not found")
        return
    if k.get("blocked"):
        bot.send_message(m.chat.id, "🚫 Key blocked")
        return
    if k["type"] == "single" and k["used_by"]:
        bot.send_message(m.chat.id, "📵 Max device reached")
        return

    users[str(m.chat.id)] = {"key": m.text}
    k["used_by"].append(m.chat.id)
    save(KEYS_FILE, keys)
    save(USERS_FILE, users)

    user_logged.add(m.chat.id)
    bot.send_message(m.chat.id, "✅ Login successful\n🎬 Send reel link")

# ========== ADMIN LOGIN ==========
@bot.message_handler(func=lambda m: m.text == "Admin")
def admin_entry(m):
    admin_wait.add(m.chat.id)
    bot.send_message(m.chat.id, "👑 Admin Panel\n🔐 Enter admin key")

@bot.message_handler(func=lambda m: m.chat.id in admin_wait)
def admin_key(m):
    if m.text != ADMIN_SECRET:
        bot.send_message(m.chat.id, "❌ Invalid admin key")
        return
    admin_wait.discard(m.chat.id)
    admin_live.add(m.chat.id)
    show_admin_panel(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "🚪 Logout")
def admin_logout(m):
    admin_live.discard(m.chat.id)
    user_welcome(m.chat.id)

# ========== EXTEND KEY ==========
@bot.message_handler(func=lambda m: m.text == "⏳ Extend Key" and m.chat.id in admin_live)
def extend_prompt(m):
    admin_ext_wait[m.chat.id] = None
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("❌ Cancel")
    bot.send_message(m.chat.id, "📌 Please send key to EXTEND", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_ext_wait and admin_ext_wait[m.chat.id] is None)
def extend_key(m):
    if m.text in ["❌ Cancel", "/start", "🚪 Logout"]:
        admin_ext_wait.pop(m.chat.id)
        show_admin_panel(m.chat.id)
        return

    if not is_key(m.text):
        bot.send_message(m.chat.id, "📌 Please send key to EXTEND")
        return

    keys = load(KEYS_FILE, {})
    if m.text not in keys:
        bot.send_message(m.chat.id, "❌ Key not found\n📌 Please send key to EXTEND")
        return

    admin_ext_wait[m.chat.id] = m.text
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ 5 Min", "➕ 1 Day", "➕ 30 Day")
    kb.add("❌ Cancel")
    bot.send_message(m.chat.id, "Select extend duration", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_ext_wait and m.text in ["➕ 5 Min","➕ 1 Day","➕ 30 Day"])
def do_extend(m):
    key = admin_ext_wait[m.chat.id]
    dmap = {"➕ 5 Min":300,"➕ 1 Day":86400,"➕ 30 Day":2592000}

    keys = load(KEYS_FILE, {})
    keys[key]["duration"] += dmap[m.text]
    keys[key]["extended"] += 1
    save(KEYS_FILE, keys)

    admin_ext_wait.pop(m.chat.id)
    bot.send_message(m.chat.id, f"✅ Key `{key}` extended", parse_mode="Markdown")
    show_admin_panel(m.chat.id)

# ========== DELETE KEY ==========
@bot.message_handler(func=lambda m: m.text == "🗑️ Delete Key" and m.chat.id in admin_live)
def delete_prompt(m):
    admin_del_wait[m.chat.id] = None
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("❌ Cancel")
    bot.send_message(m.chat.id, "📌 Please send key to DELETE", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_del_wait and admin_del_wait[m.chat.id] is None)
def delete_key(m):
    if m.text in ["❌ Cancel", "/start", "🚪 Logout"]:
        admin_del_wait.pop(m.chat.id)
        show_admin_panel(m.chat.id)
        return

    if not is_key(m.text):
        bot.send_message(m.chat.id, "📌 Please send key to DELETE")
        return

    keys = load(KEYS_FILE, {})
    if m.text not in keys:
        bot.send_message(m.chat.id, "❌ Key not found\n📌 Please send key to DELETE")
        return

    admin_del_wait[m.chat.id] = m.text
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✅ Yes Delete", "❌ Cancel")
    bot.send_message(
        m.chat.id,
        f"⚠️ Confirm delete key:\n`{m.text}`",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.chat.id in admin_del_wait and m.text == "✅ Yes Delete")
def confirm_delete(m):
    key = admin_del_wait[m.chat.id]
    keys = load(KEYS_FILE, {})
    del keys[key]
    save(KEYS_FILE, keys)

    admin_del_wait.pop(m.chat.id)
    bot.send_message(m.chat.id, f"🗑️ Key `{key}` deleted", parse_mode="Markdown")
    show_admin_panel(m.chat.id)

# ========== FALLBACK ==========
@bot.message_handler(func=lambda m: True)
def fallback(m):
    if m.text not in ["/start"]:
        bot.send_message(m.chat.id, "❌ Invalid input")

print("✅ FINAL BOT WITH CANCEL + CONFIRMATION RUNNING")
bot.polling(non_stop=True)
