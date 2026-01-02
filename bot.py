import telebot, os, json, time, shutil
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

admin_wait = set()      # waiting for admin key
admin_live = set()      # admin logged in
user_logged = set()     # user logged in (for My Key button)

# ================= HELPERS =================
def load(f, d):
    if not os.path.exists(f):
        return d
    return json.load(open(f))

def save(f, d):
    json.dump(d, open(f, "w"), indent=2)

def duration_left(sec):
    if sec <= 0:
        return "Expired"
    m = sec // 60
    if m < 60:
        return f"{m} Minutes"
    h = m // 60
    if h < 24:
        return f"{h} Hours"
    return f"{h//24} Days"

def user_status(uid):
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

# ================= INSTAGRAM =================
L = instaloader.Instaloader(download_videos=True, save_metadata=False)
cj = cookielib.MozillaCookieJar("cookies.txt")
cj.load(ignore_discard=True, ignore_expires=True)
L.context._session.cookies = cj
DOWNLOAD_DIR = "downloads"

# ================= USER UI =================
def user_welcome(cid):
    user_logged.discard(cid)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    bot.send_message(
        cid,
        "🔥 *Instagram Reel Downloader – Private Bot*\n\n"
        "🔐 Enter your key to start service\n"
        "💬 Buy key 👉 @imvrct",
        reply_markup=kb,
        parse_mode="Markdown"
    )

def show_mykey_button(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔑 My Key")
    bot.send_message(
        cid,
        "👇 *Service Active*\nSend Instagram Reel link 🎬",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    admin_wait.discard(m.chat.id)
    admin_live.discard(m.chat.id)
    user_welcome(m.chat.id)

# ================= USER KEY =================
@bot.message_handler(func=lambda m: m.text and m.text.startswith("imdhaval-") and m.chat.id not in admin_live)
def user_key(m):
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

    user_logged.add(m.chat.id)

    bot.send_message(
        m.chat.id,
        "✅ *Successfully Logged In* 🎉",
        parse_mode="Markdown"
    )
    show_mykey_button(m.chat.id)

# ================= MY KEY =================
@bot.message_handler(func=lambda m: m.text == "🔑 My Key" and m.chat.id in user_logged and m.chat.id not in admin_live)
def my_key(m):
    status, u = user_status(m.chat.id)

    if status != "active":
        bot.send_message(m.chat.id, "⚠️ Key not active\n🔐 Enter new key")
        user_logged.discard(m.chat.id)
        return

    bot.send_message(
        m.chat.id,
        f"🔑 *Your Key*\n\n"
        f"⏳ Time Left: {duration_left(int(u['expire']-time.time()))}",
        parse_mode="Markdown"
    )

# ================= REEL =================
@bot.message_handler(func=lambda m: "instagram.com/reel" in m.text and m.chat.id not in admin_live)
def reel(m):
    status, _ = user_status(m.chat.id)
    if status != "active":
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

# ================= ADMIN ENTRY =================
@bot.message_handler(func=lambda m: m.text == "Admin")
def admin_entry(m):
    admin_wait.add(m.chat.id)
    bot.send_message(
        m.chat.id,
        "👑 *Welcome to Admin Panel*\n\n🔐 Please enter admin key",
        parse_mode="Markdown"
    )

# ================= ADMIN KEY LOOP =================
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
    kb.add("➕ Generate Key", "📋 All Keys")
    kb.add("🗑️ Delete Key", "🚫 Block User")
    kb.add("🏠 Home")
    bot.send_message(cid, "👑 *Admin Panel*", reply_markup=kb, parse_mode="Markdown")

def admin_only(m):
    if m.chat.id not in admin_live:
        bot.send_message(m.chat.id, "🔐 Please login as Admin")
        return False
    return True

@bot.message_handler(func=lambda m: m.text == "🏠 Home")
def admin_home(m):
    admin_live.discard(m.chat.id)
    user_welcome(m.chat.id)

# ================= ADMIN ACTIONS =================
@bot.message_handler(func=lambda m: m.text == "➕ Generate Key")
def gen_menu(m):
    if not admin_only(m): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 Minutes", "1 Day", "30 Days")
    bot.send_message(m.chat.id, "⏳ Select duration", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_live and m.text in ["5 Minutes","1 Day","30 Days"])
def gen_key(m):
    duration = {"5 Minutes":300,"1 Day":86400,"30 Days":2592000}
    keys = load(KEYS_FILE, {})
    key = "imdhaval-" + str(int(time.time()))
    keys[key] = duration[m.text]
    save(KEYS_FILE, keys)

    bot.send_message(
        m.chat.id,
        f"✅ Key Generated\n🔑 `{key}`\n⏳ {m.text}",
        parse_mode="Markdown"
    )
    show_admin_panel(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "📋 All Keys")
def all_keys(m):
    if not admin_only(m): return
    keys = load(KEYS_FILE, {})
    if not keys:
        bot.send_message(m.chat.id, "No active keys")
        return
    txt = "📋 *All Keys*\n\n"
    for k,v in keys.items():
        txt += f"`{k}` ⏳ {duration_left(v)}\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗑️ Delete Key")
def del_prompt(m):
    if not admin_only(m): return
    bot.send_message(m.chat.id, "Enter key to delete:")
    bot.register_next_step_handler(m, do_del)

def do_del(m):
    if not admin_only(m): return
    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})

    if m.text in keys:
        del keys[m.text]

    for u in users.values():
        if u["key"] == m.text:
            u["deleted"] = True

    save(KEYS_FILE, keys)
    save(USERS_FILE, users)
    bot.send_message(m.chat.id, "🗑️ Key deleted")
    show_admin_panel(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "🚫 Block User")
def block_prompt(m):
    if not admin_only(m): return
    bot.send_message(m.chat.id, "Enter Telegram User ID:")
    bot.register_next_step_handler(m, do_block)

def do_block(m):
    if not admin_only(m): return
    users = load(USERS_FILE, {})
    if m.text in users:
        users[m.text]["blocked"] = True
        save(USERS_FILE, users)
        bot.send_message(m.chat.id, "🚫 User blocked")
    else:
        bot.send_message(m.chat.id, "❌ User not found")
    show_admin_panel(m.chat.id)

# ================= FALLBACK =================
@bot.message_handler(func=lambda m: True)
def fallback(m):
    if m.text != "/start":
        bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")

print("✅ Single Bot Running (User + Admin Secure)…")
bot.polling(non_stop=True)
