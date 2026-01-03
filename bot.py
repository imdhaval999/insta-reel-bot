import telebot, os, json, time, re
from telebot import types
from keep_alive import keep_alive

# ================= BASIC =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

bot = telebot.TeleBot(BOT_TOKEN)
keep_alive()

ADMIN_SECRET = "imdhaval"
KEY_PATTERN = re.compile(r"^imdhaval-\d+$")

KEYS_FILE = "keys.json"
USERS_FILE = "users.json"

# ================= STATES =================
admin_wait = set()
admin_live = set()
user_logged = set()

admin_gen_state = {}
admin_del_wait = set()
admin_ext_wait = {}

# ================= HELPERS =================
def load(f, d):
    if not os.path.exists(f):
        return d
    return json.load(open(f))

def save(f, d):
    json.dump(d, open(f, "w"), indent=2)

def reset_admin(chat_id):
    admin_wait.discard(chat_id)
    admin_live.discard(chat_id)
    admin_del_wait.discard(chat_id)
    admin_ext_wait.pop(chat_id, None)
    admin_gen_state.pop(chat_id, None)

def welcome_user(chat_id):
    user_logged.discard(chat_id)
    bot.send_message(
        chat_id,
        "🔥 *Instagram Reel Downloader – Private Bot*\n\n"
        "🔐 Enter your key to start service\n"
        "💬 Buy key 👉 @imvrct",
        parse_mode="Markdown"
    )

def logout_user(chat_id, reason):
    bot.send_message(chat_id, reason)
    welcome_user(chat_id)

def key_status(chat_id):
    users = load(USERS_FILE, {})
    keys = load(KEYS_FILE, {})

    u = users.get(str(chat_id))
    if not u:
        return None, "not_logged"

    key = u["key"]
    if key not in keys:
        return None, "deleted"

    k = keys[key]
    if k.get("blocked"):
        return None, "blocked"

    if time.time() > u["expire"]:
        return None, "expired"

    return key, "active"

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    reset_admin(m.chat.id)
    welcome_user(m.chat.id)

# ================= USER LOGIN =================
@bot.message_handler(func=lambda m: m.text and KEY_PATTERN.match(m.text) and m.chat.id not in admin_live)
def user_login(m):
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

# ================= URL WITHOUT KEY =================
@bot.message_handler(func=lambda m: m.text.startswith("http") and m.chat.id not in user_logged)
def no_key_url(m):
    bot.send_message(
        m.chat.id,
        "❌ Please purchase a key first\n💬 Contact @imvrct"
    )

# ================= ADMIN ENTRY =================
@bot.message_handler(func=lambda m: m.text == "Admin")
def admin_entry(m):
    admin_wait.add(m.chat.id)
    bot.send_message(
        m.chat.id,
        "👑 *Admin Panel*\n🔐 Enter admin key",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.chat.id in admin_wait)
def admin_login(m):
    if m.text == "/start":
        reset_admin(m.chat.id)
        welcome_user(m.chat.id)
        return

    if m.text != ADMIN_SECRET:
        bot.send_message(m.chat.id, "❌ Invalid admin key\n🔁 Try again")
        return

    admin_wait.discard(m.chat.id)
    admin_live.add(m.chat.id)
    show_admin_panel(m.chat.id)

# ================= ADMIN PANEL =================
def show_admin_panel(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Generate Key", "📋 All Keys")
    kb.add("🗑️ Delete Key", "⏳ Extend Key")
    kb.add("🚪 Logout")
    bot.send_message(chat_id, "👑 Admin Panel", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🚪 Logout")
def admin_logout(m):
    reset_admin(m.chat.id)
    welcome_user(m.chat.id)

# ================= GENERATE KEY =================
@bot.message_handler(func=lambda m: m.text == "➕ Generate Key" and m.chat.id in admin_live)
def gen_type(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Single User", "Multi User", "⬅ Back")
    bot.send_message(m.chat.id, "Select key type", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_live and m.text in ["Single User","Multi User"])
def gen_duration(m):
    admin_gen_state[m.chat.id] = "single" if m.text=="Single User" else "multi"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 Min","1 Day","30 Day","⬅ Back")
    bot.send_message(m.chat.id, "Select duration", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_live and m.text in ["5 Min","1 Day","30 Day"])
def gen_key(m):
    d = {"5 Min":300,"1 Day":86400,"30 Day":2592000}
    key = "imdhaval-" + str(int(time.time()))
    keys = load(KEYS_FILE,{})
    keys[key] = {
        "duration": d[m.text],
        "type": admin_gen_state[m.chat.id],
        "used_by": [],
        "blocked": False
    }
    save(KEYS_FILE, keys)
    bot.send_message(m.chat.id, f"✅ Key Generated\n🔑 `{key}`", parse_mode="Markdown")
    show_admin_panel(m.chat.id)

# ================= ALL KEYS =================
@bot.message_handler(func=lambda m: m.text == "📋 All Keys" and m.chat.id in admin_live)
def all_keys(m):
    keys = load(KEYS_FILE,{})
    if not keys:
        bot.send_message(m.chat.id, "No keys found")
        return

    txt = ""
    for k,v in keys.items():
        used = "Used" if v["used_by"] else "Not Used"
        block = (
            f"🔑 `{k}`\n"
            f"👥 {v['type']}\n"
            f"📊 {used}\n\n"
        )
        if len(txt)+len(block) > 3800:
            bot.send_message(m.chat.id, txt, parse_mode="Markdown")
            txt = block
        else:
            txt += block
    if txt:
        bot.send_message(m.chat.id, txt, parse_mode="Markdown")

# ================= BACK =================
@bot.message_handler(func=lambda m: m.text == "⬅ Back" and m.chat.id in admin_live)
def back(m):
    show_admin_panel(m.chat.id)

# ================= FALLBACK =================
@bot.message_handler(func=lambda m: True)
def fallback(m):
    # Admin mode – ignore fallback
    if m.chat.id in admin_live or m.chat.id in admin_wait:
        return

    # Logged user – ignore fallback
    if m.chat.id in user_logged:
        return

    if m.text != "/start":
        bot.send_message(m.chat.id, "❌ Key not found")

print("✅ SELLER-GRADE BOT RUNNING")
bot.polling(non_stop=True)
