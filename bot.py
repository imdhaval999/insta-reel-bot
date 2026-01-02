import telebot, os, json, time, random, string, shutil
from telebot import types
import instaloader
import http.cookiejar as cookielib
from keep_alive import keep_alive

# ================= BASIC =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
keep_alive()

ADMIN_SECRET = "imdhaval"

KEYS_FILE = "keys.json"
USERS_FILE = "users.json"

# ================= HELPERS =================
def load(file, default):
    if not os.path.exists(file):
        return default
    return json.load(open(file))

def save(file, data):
    json.dump(data, open(file, "w"), indent=2)

def gen_key():
    return "imdhaval-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

def is_active(uid):
    users = load(USERS_FILE, {})
    return str(uid) in users and time.time() < users[str(uid)]["expire"]

def duration_text(sec):
    if sec < 3600:
        return f"{sec//60} Minutes"
    if sec < 86400:
        return "1 Day"
    return "30 Days"

# ================= INSTAGRAM =================
L = instaloader.Instaloader(download_videos=True, save_metadata=False)
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
        "🔥 Instagram Reel Downloader – *Private Bot*\n\n"
        "🔐 Enter your key to start service\n\n"
        "💬 Buy key 👉 @imvrct",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ================= OWNER LOGIN =================
@bot.message_handler(func=lambda m: m.text == "👑 Owner Login")
def owner_login(m):
    msg = bot.send_message(m.chat.id, "👋 Welcome Owner\nEnter secret key 🔐")
    bot.register_next_step_handler(msg, verify_owner)

def verify_owner(m):
    if m.text.strip() != ADMIN_SECRET:
        bot.send_message(m.chat.id, "❌ Chal nikal 😄\nTu owner nahi hai")
        return
    show_admin_panel(m.chat.id)

# ================= ADMIN PANEL =================
def show_admin_panel(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Generate Key", "📋 All Keys")
    kb.add("❌ Delete Key", "🚪 Logout")
    bot.send_message(cid, "👑 *Admin Panel*", reply_markup=kb, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Generate Key")
def gen_key_menu(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 Minutes", "1 Day", "30 Days")
    bot.send_message(m.chat.id, "⏳ Select duration", reply_markup=kb)
    bot.register_next_step_handler(m, do_gen_key)

def do_gen_key(m):
    duration = {"5 Minutes":300,"1 Day":86400,"30 Days":2592000}
    if m.text not in duration:
        return
    key = gen_key()
    keys = load(KEYS_FILE, {})
    keys[key] = duration[m.text]
    save(KEYS_FILE, keys)
    bot.send_message(m.chat.id, f"✅ Key Generated\n🔑 {key}\n⏳ {m.text}")
    show_admin_panel(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "📋 All Keys")
def all_keys(m):
    keys = load(KEYS_FILE, {})
    if not keys:
        bot.send_message(m.chat.id, "No active keys")
        return
    txt = f"📋 *All Keys* (Total: {len(keys)})\n\n"
    for k,v in keys.items():
        txt += f"🔑 `{k}` ⏳ {duration_text(v)}\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "❌ Delete Key")
def del_key(m):
    msg = bot.send_message(m.chat.id, "Enter key to delete:")
    bot.register_next_step_handler(msg, do_del_key)

def do_del_key(m):
    keys = load(KEYS_FILE, {})
    if m.text in keys:
        del keys[m.text]
        save(KEYS_FILE, keys)
        bot.send_message(m.chat.id, "✅ Key successfully deleted")
    else:
        bot.send_message(m.chat.id, "❌ Key not found")
    show_admin_panel(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "🚪 Logout")
def logout(m):
    bot.send_message(m.chat.id, "🚪 Logged out successfully\n/start again")
    start(m)

# ================= USER KEY FLOW =================
@bot.message_handler(func=lambda m: m.text.startswith("imdhaval-"))
def check_key(m):
    bot.send_message(m.chat.id, "⏳ Checking your key...")
    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})

    if m.text not in keys:
        bot.send_message(m.chat.id, "❌ Wrong key, try again\n💬 Buy key 👉 @imvrct")
        return

    users[str(m.chat.id)] = {
        "expire": time.time() + keys[m.text]
    }
    duration = duration_text(keys[m.text])
    del keys[m.text]
    save(KEYS_FILE, keys)
    save(USERS_FILE, users)

    bot.send_message(
        m.chat.id,
        f"✅ Successfully Logged In 🎉\n\n"
        f"⏳ Duration: {duration}\n"
        f"👇 Enter Instagram Reel link 🎬"
    )

# ================= REEL =================
@bot.message_handler(func=lambda m: "instagram.com/reel" in m.text)
def reel(m):
    if not is_active(m.chat.id):
        bot.send_message(m.chat.id, "⏰ Key expired\nEnter new key or DM 👉 @imvrct")
        return
    try:
        sc = m.text.split("/")[-2]
        msg = bot.send_message(m.chat.id, "⏳ Downloading reel...")
        post = instaloader.Post.from_shortcode(L.context, sc)
        if os.path.exists(DOWNLOAD_DIR):
            shutil.rmtree(DOWNLOAD_DIR)
        os.mkdir(DOWNLOAD_DIR)
        L.download_post(post, target=DOWNLOAD_DIR)
        for f in os.listdir(DOWNLOAD_DIR):
            if f.endswith(".mp4"):
                with open(os.path.join(DOWNLOAD_DIR,f),"rb") as v:
                    bot.send_video(m.chat.id, v, caption=post.caption or "")
                break
        shutil.rmtree(DOWNLOAD_DIR)
        bot.delete_message(m.chat.id, msg.message_id)
    except:
        bot.send_message(m.chat.id, "❌ Failed to download")

print("✅ Stable Paid Reel Bot Running…")
bot.polling(non_stop=True)
