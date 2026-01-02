import telebot, os, json, time, random, string
from telebot import types
from keep_alive import keep_alive

# ================= BASIC =================
BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("ADMIN_BOT_TOKEN missing")

bot = telebot.TeleBot(BOT_TOKEN)
keep_alive()

ADMIN_SECRET = "imdhaval"

KEYS_FILE = "keys.json"
USERS_FILE = "users.json"
SALES_FILE = "sales.json"

admin_sessions = set()
admin_waiting = set()

# ================= HELPERS =================
def load(file, default):
    if not os.path.exists(file):
        return default
    return json.load(open(file))

def save(file, data):
    json.dump(data, open(file, "w"), indent=2)

def gen_key():
    return "imdhaval-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

def ensure_sales():
    if not os.path.exists(SALES_FILE):
        save(SALES_FILE, {
            "total_generated": 0,
            "total_sold": 0,
            "total_downloads": 0
        })

def duration_text(sec):
    if sec < 3600:
        return f"{sec//60} Minutes"
    if sec < 86400:
        return "1 Day"
    return "30 Days"

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    admin_sessions.discard(m.chat.id)
    admin_waiting.add(m.chat.id)
    bot.send_message(
        m.chat.id,
        "👑 *Admin Panel Login*\n\n"
        "🔐 Enter admin secret key",
        parse_mode="Markdown"
    )

# ================= ADMIN LOGIN LOOP =================
@bot.message_handler(func=lambda m: m.chat.id in admin_waiting)
def admin_login(m):
    if m.text.strip() != ADMIN_SECRET:
        bot.send_message(
            m.chat.id,
            "❌ Wrong admin key\n🔁 Try again"
        )
        return

    admin_waiting.discard(m.chat.id)
    admin_sessions.add(m.chat.id)
    show_panel(m.chat.id)

# ================= PANEL =================
def show_panel(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Generate Key", "📋 All Keys")
    kb.add("🚫 Block User", "🗑️ Delete Key")
    kb.add("🔁 Renew User", "📊 Stats")
    kb.add("🚪 Logout")
    bot.send_message(
        cid,
        "👑 *Admin Control Panel*",
        reply_markup=kb,
        parse_mode="Markdown"
    )

def admin_only(m):
    if m.chat.id not in admin_sessions:
        bot.send_message(m.chat.id, "🔐 Please login as admin")
        return False
    return True

# ================= GENERATE KEY =================
@bot.message_handler(func=lambda m: m.text == "➕ Generate Key")
def gen_menu(m):
    if not admin_only(m): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 Minutes", "1 Day", "30 Days")
    bot.send_message(m.chat.id, "⏳ Select key duration", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_sessions and m.text in ["5 Minutes","1 Day","30 Days"])
def do_gen(m):
    ensure_sales()
    duration = {"5 Minutes":300,"1 Day":86400,"30 Days":2592000}

    key = gen_key()
    keys = load(KEYS_FILE, {})
    keys[key] = duration[m.text]
    save(KEYS_FILE, keys)

    sales = load(SALES_FILE, {})
    sales["total_generated"] += 1
    save(SALES_FILE, sales)

    bot.send_message(
        m.chat.id,
        f"✅ *Key Generated*\n\n"
        f"🔑 `{key}`\n"
        f"⏳ {m.text}",
        parse_mode="Markdown"
    )
    show_panel(m.chat.id)

# ================= ALL KEYS =================
@bot.message_handler(func=lambda m: m.text == "📋 All Keys")
def all_keys(m):
    if not admin_only(m): return
    keys = load(KEYS_FILE, {})
    if not keys:
        bot.send_message(m.chat.id, "No active keys")
        return

    txt = f"📋 *All Keys* (Total: {len(keys)})\n\n"
    for k,v in keys.items():
        txt += f"🔑 `{k}` ⏳ {duration_text(v)}\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

# ================= DELETE KEY =================
@bot.message_handler(func=lambda m: m.text == "🗑️ Delete Key")
def del_prompt(m):
    if not admin_only(m): return
    bot.send_message(m.chat.id, "🔑 Enter key to delete")
    bot.register_next_step_handler(m, do_delete)

def do_delete(m):
    if not admin_only(m): return
    keys = load(KEYS_FILE, {})
    if m.text in keys:
        del keys[m.text]
        save(KEYS_FILE, keys)
        bot.send_message(m.chat.id, "✅ Key deleted")
    else:
        bot.send_message(m.chat.id, "❌ Key not found")
    show_panel(m.chat.id)

# ================= BLOCK USER =================
@bot.message_handler(func=lambda m: m.text == "🚫 Block User")
def block_prompt(m):
    if not admin_only(m): return
    bot.send_message(m.chat.id, "Enter Telegram User ID to block:")
    bot.register_next_step_handler(m, do_block)

def do_block(m):
    if not admin_only(m): return
    users = load(USERS_FILE, {})
    u = users.get(m.text.strip())
    if not u:
        bot.send_message(m.chat.id, "❌ User not found")
    else:
        u["blocked"] = True
        save(USERS_FILE, users)
        bot.send_message(m.chat.id, "🚫 User blocked")
    show_panel(m.chat.id)

# ================= RENEW USER =================
@bot.message_handler(func=lambda m: m.text == "🔁 Renew User")
def renew_prompt(m):
    if not admin_only(m): return
    bot.send_message(m.chat.id, "Enter Telegram User ID:")
    bot.register_next_step_handler(m, do_renew)

def do_renew(m):
    if not admin_only(m): return
    users = load(USERS_FILE, {})
    u = users.get(m.text.strip())
    if not u:
        bot.send_message(m.chat.id, "❌ User not found")
    else:
        u["expire"] += 86400
        save(USERS_FILE, users)
        bot.send_message(m.chat.id, "✅ User renewed for 1 Day")
    show_panel(m.chat.id)

# ================= STATS =================
@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def stats(m):
    if not admin_only(m): return
    ensure_sales()
    sales = load(SALES_FILE, {})
    users = load(USERS_FILE, {})
    txt = (
        f"📊 *Stats*\n\n"
        f"🔑 Generated: {sales['total_generated']}\n"
        f"💰 Sold: {sales['total_sold']}\n"
        f"👤 Active Users: {len(users)}\n"
        f"🎬 Total Downloads: {sales['total_downloads']}"
    )
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

# ================= LOGOUT =================
@bot.message_handler(func=lambda m: m.text == "🚪 Logout")
def logout(m):
    admin_sessions.discard(m.chat.id)
    admin_waiting.discard(m.chat.id)
    bot.send_message(m.chat.id, "🚪 Logged out\n/start again")

print("✅ Admin Bot Running…")
bot.polling(non_stop=True)
