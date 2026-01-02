import telebot, os, json, time, random, string, shutil
import instaloader
import http.cookiejar as cookielib
from telebot import types
from keep_alive import keep_alive

# ================= BASIC =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

bot = telebot.TeleBot(BOT_TOKEN)
keep_alive()

ADMIN_SECRET = "imdhaval"   # 👑 initial admin key

KEYS_FILE = "keys.json"
USERS_FILE = "users.json"

# ================= HELPERS =================
def load(file, default):
    if not os.path.exists(file):
        return default
    return json.load(open(file))

def save(file, data):
    json.dump(data, open(file, "w"), indent=2)

def generate_key():
    return "VENOM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

def active_user(uid):
    users = load(USERS_FILE, {})
    return str(uid) in users and time.time() < users[str(uid)]

def duration_text(sec):
    if sec < 3600:
        return f"{sec//60} Minutes"
    if sec < 86400:
        return "1 Day"
    return "30 Days"

# ================= INSTALOADER =================
L = instaloader.Instaloader(
    download_videos=True,
    save_metadata=False,
    post_metadata_txt_pattern=""
)

cj = cookielib.MozillaCookieJar("cookies.txt")
cj.load(ignore_discard=True, ignore_expires=True)
L.context._session.cookies = cj

DOWNLOAD_DIR = "downloads"

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👑 Owner Login")
    bot.send_message(
        m.chat.id,
        "🔥 *Instagram Reel Downloader – Private Bot*\n\n"
        "🎬 Download reels in HD quality\n"
        "🔐 *Enter your key to start service*\n\n"
        "💬 To buy key DM 👉 @imvrct",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ================= OWNER LOGIN =================
@bot.message_handler(func=lambda m: m.text == "👑 Owner Login")
def owner_login(m):
    bot.send_message(
        m.chat.id,
        "👋 *Welcome Owner*\nPlease enter your secret key 🔐",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(m, verify_owner)

def verify_owner(m):
    global ADMIN_SECRET
    if m.text.strip() != ADMIN_SECRET:
        bot.send_message(m.chat.id, "❌ Chal nikal 😄\nTu owner nahi hai")
        return
    admin_panel(m.chat.id)

# ================= ADMIN PANEL =================
def admin_panel(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Generate Key", "❌ Remove Key")
    kb.add("🚫 Block User", "🔁 Change Admin Key")
    kb.add("⬅️ Exit")
    bot.send_message(
        cid,
        "👑 *Admin Control Panel*",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text == "➕ Generate Key")
def gen_key(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 Minutes", "1 Day", "30 Days")
    bot.send_message(m.chat.id, "⏳ Select key duration:", reply_markup=kb)
    bot.register_next_step_handler(m, create_key)

def create_key(m):
    duration = {
        "5 Minutes": 300,
        "1 Day": 86400,
        "30 Days": 2592000
    }
    if m.text not in duration:
        bot.send_message(m.chat.id, "❌ Invalid option")
        return

    key = generate_key()
    keys = load(KEYS_FILE, {})
    keys[key] = duration[m.text]
    save(KEYS_FILE, keys)

    bot.send_message(
        m.chat.id,
        f"✅ *Key Generated*\n\n"
        f"🔑 `{key}`\n"
        f"⏳ Duration: {m.text}",
        parse_mode="Markdown"
    )
    admin_panel(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "❌ Remove Key")
def rem_key(m):
    bot.send_message(m.chat.id, "Send key to remove:")
    bot.register_next_step_handler(m, do_remove)

def do_remove(m):
    keys = load(KEYS_FILE, {})
    if m.text in keys:
        del keys[m.text]
        save(KEYS_FILE, keys)
        bot.send_message(m.chat.id, "🗑️ Key removed")
    else:
        bot.send_message(m.chat.id, "❌ Key not found")
    admin_panel(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "🚫 Block User")
def block_user(m):
    bot.send_message(m.chat.id, "Send Telegram User ID:")
    bot.register_next_step_handler(m, do_block)

def do_block(m):
    users = load(USERS_FILE, {})
    users.pop(m.text.strip(), None)
    save(USERS_FILE, users)
    bot.send_message(m.chat.id, "🚫 User blocked")
    admin_panel(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "🔁 Change Admin Key")
def change_admin(m):
    bot.send_message(m.chat.id, "Enter new admin secret key:")
    bot.register_next_step_handler(m, do_change_admin)

def do_change_admin(m):
    global ADMIN_SECRET
    ADMIN_SECRET = m.text.strip()
    bot.send_message(m.chat.id, "✅ Admin key changed successfully")
    admin_panel(m.chat.id)

# ================= USER KEY =================
@bot.message_handler(func=lambda m: m.text and not active_user(m.chat.id) and m.text.startswith("VENOM"))
def user_key(m):
    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})

    if m.text not in keys:
        bot.send_message(
            m.chat.id,
            "❌ Invalid key\n\n"
            "Please enter valid key\n"
            "or DM to buy 👉 @imvrct"
        )
        return

    expire = time.time() + keys[m.text]
    users[str(m.chat.id)] = expire
    duration = duration_text(keys[m.text])

    del keys[m.text]
    save(KEYS_FILE, keys)
    save(USERS_FILE, users)

    bot.send_message(
        m.chat.id,
        f"✅ *Successfully Logged In* 🎉\n\n"
        f"⏳ *Key Duration:* {duration}\n"
        f"🚀 *Service Activated*\n\n"
        f"👇 *Enter Instagram Reel Link to Download* 🎬",
        parse_mode="Markdown"
    )

# ================= REEL =================
@bot.message_handler(func=lambda m: "instagram.com/reel" in m.text)
def reel(m):
    if not active_user(m.chat.id):
        bot.send_message(
            m.chat.id,
            "⏰ Your key expired\n\n"
            "🔐 Enter new key\n"
            "or DM 👉 @imvrct"
        )
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
        bot.send_message(m.chat.id, "❌ Failed to download reel")

print("✅ Private Paid Reel Bot Running…")
bot.polling(non_stop=True)
