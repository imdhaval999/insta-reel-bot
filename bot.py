import telebot, os, json, time, re
from telebot import types
from keep_alive import keep_alive

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
keep_alive()

ADMIN_SECRET = "imdhaval"
KEY_REGEX = re.compile(r"^imdhaval-\d+$")

KEYS_FILE = "keys.json"
USERS_FILE = "users.json"

# ================= STATE =================
admin_wait = set()
admin_live = set()

admin_gen_type = {}
admin_wait_delete = set()
admin_wait_extend = {}

user_logged = set()

# ================= HELPERS =================
def load(path, default):
    if not os.path.exists(path):
        return default
    return json.load(open(path))

def save(path, data):
    json.dump(data, open(path, "w"), indent=2)

def reset_admin(cid):
    admin_wait.discard(cid)
    admin_live.discard(cid)
    admin_gen_type.pop(cid, None)
    admin_wait_delete.discard(cid)
    admin_wait_extend.pop(cid, None)

def remove_keyboard(cid):
    bot.send_message(cid, " ", reply_markup=types.ReplyKeyboardRemove())

def welcome(cid):
    user_logged.discard(cid)
    remove_keyboard(cid)
    bot.send_message(
        cid,
        "🔥 *Instagram Reel Downloader – Private Bot*\n\n"
        "🔐 Enter your key to start service\n"
        "💬 Buy key 👉 @imvrct"
    )

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    reset_admin(m.chat.id)
    welcome(m.chat.id)

# ================= ADMIN ENTRY =================
@bot.message_handler(func=lambda m: m.text == "Admin")
def admin_entry(m):
    reset_admin(m.chat.id)
    admin_wait.add(m.chat.id)
    bot.send_message(
        m.chat.id,
        "👑 *Admin Panel*\n🔐 Enter admin key"
    )

@bot.message_handler(func=lambda m: m.chat.id in admin_wait)
def admin_login(m):
    if m.text == "/start":
        reset_admin(m.chat.id)
        welcome(m.chat.id)
        return

    if m.text != ADMIN_SECRET:
        bot.send_message(m.chat.id, "❌ Invalid admin key\n🔁 Try again")
        return

    admin_wait.discard(m.chat.id)
    admin_live.add(m.chat.id)
    show_admin_panel(m.chat.id)

# ================= ADMIN PANEL =================
def show_admin_panel(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Generate Key", "📋 All Keys")
    kb.add("🗑️ Delete Key", "⏳ Extend Key")
    kb.add("🚪 Logout")
    bot.send_message(cid, "👑 *Admin Panel*", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🚪 Logout" and m.chat.id in admin_live)
def admin_logout(m):
    reset_admin(m.chat.id)
    welcome(m.chat.id)

# ================= GENERATE KEY =================
@bot.message_handler(func=lambda m: m.text == "➕ Generate Key" and m.chat.id in admin_live)
def gen_key_type(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Single User", "Multi User", "⬅ Back")
    bot.send_message(m.chat.id, "Select key type", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_live and m.text in ["Single User","Multi User"])
def gen_key_duration(m):
    admin_gen_type[m.chat.id] = "single" if m.text=="Single User" else "multi"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 Min","1 Day","30 Day","⬅ Back")
    bot.send_message(m.chat.id, "Select duration", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_live and m.text in ["5 Min","1 Day","30 Day"])
def gen_key_done(m):
    dur = {"5 Min":300,"1 Day":86400,"30 Day":2592000}
    key = f"imdhaval-{int(time.time())}"
    keys = load(KEYS_FILE,{})
    keys[key] = {
        "duration": dur[m.text],
        "type": admin_gen_type[m.chat.id],
        "used_by": [],
        "blocked": False
    }
    save(KEYS_FILE, keys)
    bot.send_message(m.chat.id, f"✅ Key Generated\n🔑 `{key}`")
    show_admin_panel(m.chat.id)

# ================= ALL KEYS =================
@bot.message_handler(func=lambda m: m.text == "📋 All Keys" and m.chat.id in admin_live)
def all_keys(m):
    keys = load(KEYS_FILE,{})
    if not keys:
        bot.send_message(m.chat.id, "No keys found")
        return
    out = ""
    for k,v in keys.items():
        used = "Used" if v["used_by"] else "Not Used"
        out += f"🔑 `{k}`\n👥 {v['type']}\n📊 {used}\n\n"
    bot.send_message(m.chat.id, out)

# ================= DELETE KEY =================
@bot.message_handler(func=lambda m: m.text == "🗑️ Delete Key" and m.chat.id in admin_live)
def del_prompt(m):
    admin_wait_delete.add(m.chat.id)
    bot.send_message(m.chat.id, "📌 Send key to delete")

@bot.message_handler(func=lambda m: m.chat.id in admin_wait_delete)
def del_key(m):
    if not KEY_REGEX.match(m.text):
        bot.send_message(m.chat.id, "❌ Invalid key format")
        return
    keys = load(KEYS_FILE,{})
    if m.text not in keys:
        bot.send_message(m.chat.id, "❌ Key not found")
        return
    del keys[m.text]
    save(KEYS_FILE, keys)
    admin_wait_delete.discard(m.chat.id)
    bot.send_message(m.chat.id, "🗑️ Key deleted successfully")
    show_admin_panel(m.chat.id)

# ================= EXTEND KEY =================
@bot.message_handler(func=lambda m: m.text == "⏳ Extend Key" and m.chat.id in admin_live)
def ext_prompt(m):
    admin_wait_extend[m.chat.id] = None
    bot.send_message(m.chat.id, "📌 Send key to extend")

@bot.message_handler(func=lambda m: m.chat.id in admin_wait_extend and admin_wait_extend[m.chat.id] is None)
def ext_key(m):
    if not KEY_REGEX.match(m.text):
        bot.send_message(m.chat.id, "❌ Invalid key format")
        return
    keys = load(KEYS_FILE,{})
    if m.text not in keys:
        bot.send_message(m.chat.id, "❌ Key not found")
        return
    admin_wait_extend[m.chat.id] = m.text
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 Min","1 Day","30 Day","⬅ Back")
    bot.send_message(m.chat.id, "Select extend duration", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_wait_extend and m.text in ["5 Min","1 Day","30 Day"])
def ext_done(m):
    dur = {"5 Min":300,"1 Day":86400,"30 Day":2592000}
    key = admin_wait_extend[m.chat.id]
    keys = load(KEYS_FILE,{})
    keys[key]["duration"] += dur[m.text]
    save(KEYS_FILE, keys)
    admin_wait_extend.pop(m.chat.id, None)
    bot.send_message(m.chat.id, "⏳ Key extended successfully")
    show_admin_panel(m.chat.id)

# ================= USER LOGIN =================
@bot.message_handler(func=lambda m: KEY_REGEX.match(m.text) and m.chat.id not in admin_live)
def user_login(m):
    keys = load(KEYS_FILE,{})
    users = load(USERS_FILE,{})
    key = m.text

    if key not in keys:
        bot.send_message(m.chat.id, "❌ Key not found")
        return

    k = keys[key]
    if k.get("blocked"):
        bot.send_message(m.chat.id, "🚫 Key blocked")
        return

    if k["type"] == "single" and k["used_by"]:
        bot.send_message(m.chat.id, "📵 Max device reached")
        return

    users[str(m.chat.id)] = {
        "key": key,
        "expire": time.time() + k["duration"]
    }
    k["used_by"].append(m.chat.id)

    save(KEYS_FILE, keys)
    save(USERS_FILE, users)
    user_logged.add(m.chat.id)

    bot.send_message(m.chat.id, "✅ Login successful 🎉\nSend reel link 🎬")

# ================= URL WITHOUT KEY =================
@bot.message_handler(func=lambda m: m.text.startswith("http") and m.chat.id not in user_logged)
def url_without_key(m):
    bot.send_message(
        m.chat.id,
        "❌ Please purchase a key first\n💬 Contact @imvrct"
    )

# ================= FALLBACK =================
@bot.message_handler(func=lambda m: True)
def fallback(m):
    if m.chat.id in admin_live or m.chat.id in admin_wait:
        return
    if m.chat.id in user_logged:
        return
    if m.text != "/start":
        bot.send_message(m.chat.id, "❌ Key not found")

print("✅ FINAL SELLER-GRADE BOT RUNNING")
bot.polling(non_stop=True)
