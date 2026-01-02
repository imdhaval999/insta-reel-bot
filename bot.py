import telebot
import instaloader
import os, shutil, json
import http.cookiejar as cookielib
from telebot import types
from keep_alive import keep_alive

# ================= BASIC =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

ADMIN_SECRET = "imdhaval"   # 🔐 CHANGE THIS

bot = telebot.TeleBot(BOT_TOKEN)
keep_alive()

KEY_FILE = "keys.txt"
USED_KEYS_FILE = "used_keys.json"
ADMINS_FILE = "admins.json"

# ================= FILE UTILS =================

def load_keys():
    if not os.path.exists(KEY_FILE): return []
    return [k.strip() for k in open(KEY_FILE) if k.strip()]

def save_keys(keys):
    with open(KEY_FILE, "w") as f:
        f.write("\n".join(keys))

def load_used():
    if not os.path.exists(USED_KEYS_FILE): return {}
    return json.load(open(USED_KEYS_FILE))

def save_used(data):
    json.dump(data, open(USED_KEYS_FILE, "w"))

def load_admins():
    if not os.path.exists(ADMINS_FILE): return []
    return json.load(open(ADMINS_FILE))

def save_admins(data):
    json.dump(data, open(ADMINS_FILE, "w"))

def is_admin(uid):
    return uid in load_admins()

# ================= INSTALOADER =================

L = instaloader.Instaloader(
    download_videos=True,
    download_video_thumbnails=False,
    download_comments=False,
    save_metadata=False,
    post_metadata_txt_pattern=""
)

cookiejar = cookielib.MozillaCookieJar("cookies.txt")
cookiejar.load(ignore_discard=True, ignore_expires=True)
L.context._session.cookies = cookiejar

DOWNLOAD_DIR = "downloads"

# ================= START =================

@bot.message_handler(commands=["start"])
def start(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👑 Owner Login")
    bot.send_message(
        message.chat.id,
        "🔐 *Paid Reel Downloader Bot*\n\n"
        "🔑 Users: send your key\n"
        "👑 Owner: login to manage keys",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ================= OWNER LOGIN =================

@bot.message_handler(func=lambda m: m.text == "👑 Owner Login")
def owner_login(message):
    bot.send_message(
        message.chat.id,
        "🔐 Send *Admin Secret Key*",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(message, verify_admin)

def verify_admin(message):
    if message.text.strip() == ADMIN_SECRET:
        admins = load_admins()
        if message.chat.id not in admins:
            admins.append(message.chat.id)
            save_admins(admins)
        show_admin_panel(message.chat.id)
    else:
        bot.send_message(message.chat.id, "❌ Invalid admin key")

# ================= ADMIN PANEL =================

def show_admin_panel(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📋 View Keys", "➕ Add Key")
    kb.add("❌ Delete Key", "🚫 Revoke User")
    kb.add("⬅️ Exit Admin")
    bot.send_message(
        chat_id,
        "👑 *Admin Panel*",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: is_admin(m.chat.id) and m.text == "📋 View Keys")
def view_keys(message):
    keys = load_keys()
    used = load_used()
    text = "📋 *ALL KEYS*\n\n"
    for k in keys:
        text += f"🔑 `{k}`\n"
    for k,u in used.items():
        text += f"🚫 `{k}` → {u}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: is_admin(m.chat.id) and m.text == "➕ Add Key")
def add_key(message):
    bot.send_message(message.chat.id, "Send new key:")
    bot.register_next_step_handler(message, save_new_key)

def save_new_key(message):
    keys = load_keys()
    keys.append(message.text.strip())
    save_keys(keys)
    bot.send_message(message.chat.id, "✅ Key added")
    show_admin_panel(message.chat.id)

@bot.message_handler(func=lambda m: is_admin(m.chat.id) and m.text == "❌ Delete Key")
def del_key(message):
    bot.send_message(message.chat.id, "Send key to delete:")
    bot.register_next_step_handler(message, delete_key_now)

def delete_key_now(message):
    keys = load_keys()
    used = load_used()
    k = message.text.strip()
    if k in keys:
        keys.remove(k)
        save_keys(keys)
    if k in used:
        del used[k]
        save_used(used)
    bot.send_message(message.chat.id, "🗑️ Key deleted")
    show_admin_panel(message.chat.id)

@bot.message_handler(func=lambda m: is_admin(m.chat.id) and m.text == "🚫 Revoke User")
def revoke_user(message):
    bot.send_message(message.chat.id, "Send Telegram User ID:")
    bot.register_next_step_handler(message, revoke_user_now)

def revoke_user_now(message):
    uid = message.text.strip()
    used = load_used()
    for k,u in list(used.items()):
        if str(u) == uid:
            del used[k]
    save_used(used)
    bot.send_message(message.chat.id, "🚫 User access revoked")
    show_admin_panel(message.chat.id)

@bot.message_handler(func=lambda m: is_admin(m.chat.id) and m.text == "⬅️ Exit Admin")
def exit_admin(message):
    admins = load_admins()
    admins.remove(message.chat.id)
    save_admins(admins)
    bot.send_message(message.chat.id, "Exited admin mode. /start again")

# ================= USER DOWNLOAD =================

def user_has_access(uid):
    return uid in load_used().values()

@bot.message_handler(func=lambda m: m.text and "instagram.com/reel" in m.text)
def download_reel(message):
    if not user_has_access(message.chat.id):
        bot.send_message(message.chat.id, "🔒 Access denied. Send valid key.")
        return

    try:
        shortcode = message.text.strip().split("/")[-2]
        msg = bot.send_message(message.chat.id, "⏳ Downloading…")

        post = instaloader.Post.from_shortcode(L.context, shortcode)

        if os.path.exists(DOWNLOAD_DIR): shutil.rmtree(DOWNLOAD_DIR)
        os.mkdir(DOWNLOAD_DIR)
        L.download_post(post, target=DOWNLOAD_DIR)

        for f in os.listdir(DOWNLOAD_DIR):
            if f.endswith(".mp4"):
                with open(os.path.join(DOWNLOAD_DIR, f), "rb") as v:
                    bot.send_video(message.chat.id, v, caption=post.caption or "")
                break

        shutil.rmtree(DOWNLOAD_DIR)
        bot.delete_message(message.chat.id, msg.message_id)

    except:
        bot.send_message(message.chat.id, "❌ Failed to download")

print("✅ Admin + Seller Bot Running…")
bot.polling(non_stop=True)
