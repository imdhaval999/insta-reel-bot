import telebot
import threading
import os, json, time, shutil, random, string
import instaloader
import http.cookiejar as cookielib
from telebot import types
from keep_alive import keep_alive

# ================= KEEP ALIVE =================
keep_alive()

# ================= TOKENS =================
USER_TOKEN  = os.getenv("USER_BOT_TOKEN")
ADMIN_TOKEN = os.getenv("ADMIN_BOT_TOKEN")

if not USER_TOKEN or not ADMIN_TOKEN:
    raise ValueError("USER_BOT_TOKEN or ADMIN_BOT_TOKEN missing")

user_bot  = telebot.TeleBot(USER_TOKEN)
admin_bot = telebot.TeleBot(ADMIN_TOKEN)

# ================= FILES =================
KEYS_FILE  = "keys.json"
USERS_FILE = "users.json"

# ================= ADMIN =================
ADMIN_SECRET = "imdhaval"
admin_logged = set()

# ================= HELPERS =================
def load(f, d):
    if not os.path.exists(f):
        return d
    return json.load(open(f))

def save(f, d):
    json.dump(d, open(f, "w"), indent=2)

def gen_key():
    return "imdhaval-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

def duration_text(sec):
    if sec <= 0:
        return "Expired"
    m = sec // 60
    if m < 60:
        return f"{m} Minutes"
    h = m // 60
    if h < 24:
        return f"{h} Hours"
    return f"{h//24} Days"

# ================= INSTAGRAM =================
L = instaloader.Instaloader(download_videos=True, save_metadata=False)
cj = cookielib.MozillaCookieJar("cookies.txt")
cj.load(ignore_discard=True, ignore_expires=True)
L.context._session.cookies = cj
DOWNLOAD_DIR = "downloads"

# ================= USER HELPERS =================
def welcome_user(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔑 My Key")
    user_bot.send_message(
        cid,
        "🔥 *Instagram Reel Downloader – Private Bot*\n\n"
        "🔐 Enter your key to start service\n"
        "💬 Buy key 👉 @imvrct",
        reply_markup=kb,
        parse_mode="Markdown"
    )

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

# ================= USER BOT =================
@user_bot.message_handler(commands=["start"])
def user_start(m):
    welcome_user(m.chat.id)

@user_bot.message_handler(func=lambda m: m.text == "🔑 My Key")
def my_key(m):
    status, u = user_status(m.chat.id)

    if status == "none":
        user_bot.send_message(m.chat.id, "❌ No key found\n🔐 Enter your key")
        return

    if status == "active":
        msg = (
            f"🔑 *Your Key*\n\n"
            f"📌 Status: Active ✅\n"
            f"⏳ Time Left: {duration_text(int(u['expire']-time.time()))}"
        )
    elif status == "blocked":
        msg = "🚫 *Your key is BLOCKED by admin*\n🔐 Enter new key"
    elif status == "deleted":
        msg = "🗑️ *Your key is DELETED by admin*\n🔐 Enter new key"
    else:
        msg = "⏰ *Your key is EXPIRED*\n🔐 Enter new key"

    user_bot.send_message(m.chat.id, msg, parse_mode="Markdown")

@user_bot.message_handler(func=lambda m: m.text and m.text.startswith("imdhaval-"))
def user_key(m):
    user_bot.send_message(m.chat.id, "⏳ Checking your key…")

    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})

    if m.text not in keys:
        user_bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")
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

    user_bot.send_message(
        m.chat.id,
        f"✅ *Successfully Logged In* 🎉\n"
        f"⏳ Duration: {duration_text(int(users[str(m.chat.id)]['expire']-time.time()))}\n"
        f"👇 Send Instagram Reel link",
        parse_mode="Markdown"
    )

@user_bot.message_handler(func=lambda m: "instagram.com/reel" in m.text)
def reel_download(m):
    status, u = user_status(m.chat.id)

    if status != "active":
        if status == "blocked":
            user_bot.send_message(m.chat.id, "🚫 Your key is blocked\n🔐 Enter new key")
        elif status == "deleted":
            user_bot.send_message(m.chat.id, "🗑️ Your key is deleted\n🔐 Enter new key")
        elif status == "expired":
            user_bot.send_message(m.chat.id, "⏰ Key expired\n🔐 Enter new key")
        else:
            user_bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")
        return

    try:
        sc = m.text.split("/")[-2]
        msg = user_bot.send_message(m.chat.id, "⏳ Downloading reel…")

        post = instaloader.Post.from_shortcode(L.context, sc)

        if os.path.exists(DOWNLOAD_DIR):
            shutil.rmtree(DOWNLOAD_DIR)
        os.mkdir(DOWNLOAD_DIR)

        L.download_post(post, target=DOWNLOAD_DIR)

        sent = False
        for f in os.listdir(DOWNLOAD_DIR):
            if f.endswith(".mp4"):
                with open(os.path.join(DOWNLOAD_DIR, f), "rb") as v:
                    user_bot.send_video(m.chat.id, v, caption=post.caption or "")
                sent = True
                break

        shutil.rmtree(DOWNLOAD_DIR)
        user_bot.delete_message(m.chat.id, msg.message_id)

        if not sent:
            user_bot.send_message(m.chat.id, "❌ Video not found")

    except Exception:
        if os.path.exists(DOWNLOAD_DIR):
            shutil.rmtree(DOWNLOAD_DIR)
        user_bot.send_message(m.chat.id, "❌ Failed to download reel")

@user_bot.message_handler(func=lambda m: True)
def user_fallback(m):
    if m.text != "/start":
        user_bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")

# ================= ADMIN BOT =================
@admin_bot.message_handler(commands=["start"])
def admin_start(m):
    admin_logged.discard(m.chat.id)
    admin_bot.send_message(
        m.chat.id,
        "👑 *Admin Panel Login*\n\n🔐 Enter admin key",
        parse_mode="Markdown"
    )

@admin_bot.message_handler(func=lambda m: m.chat.id not in admin_logged)
def admin_login(m):
    if m.text.strip() != ADMIN_SECRET:
        admin_bot.send_message(m.chat.id, "❌ Wrong admin key\n🔁 Try again")
        return
    admin_logged.add(m.chat.id)
    show_admin_panel(m.chat.id)

def show_admin_panel(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Generate Key", "📋 All Keys")
    kb.add("🚫 Block User", "🗑️ Delete Key")
    kb.add("🚪 Logout")
    admin_bot.send_message(cid, "👑 *Admin Panel*", reply_markup=kb, parse_mode="Markdown")

@admin_bot.message_handler(func=lambda m: m.chat.id in admin_logged and m.text == "➕ Generate Key")
def admin_gen(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 Minutes", "1 Day", "30 Days")
    admin_bot.send_message(m.chat.id, "⏳ Select duration", reply_markup=kb)

@admin_bot.message_handler(func=lambda m: m.chat.id in admin_logged and m.text in ["5 Minutes","1 Day","30 Days"])
def admin_do_gen(m):
    duration = {"5 Minutes":300,"1 Day":86400,"30 Days":2592000}
    keys = load(KEYS_FILE, {})
    key = gen_key()
    keys[key] = duration[m.text]
    save(KEYS_FILE, keys)

    admin_bot.send_message(
        m.chat.id,
        f"✅ Key Generated\n🔑 `{key}`\n⏳ {m.text}",
        parse_mode="Markdown"
    )
    show_admin_panel(m.chat.id)

@admin_bot.message_handler(func=lambda m: m.chat.id in admin_logged and m.text == "📋 All Keys")
def admin_all_keys(m):
    keys = load(KEYS_FILE, {})
    if not keys:
        admin_bot.send_message(m.chat.id, "No active keys")
        return
    txt = "📋 *All Keys*\n\n"
    for k,v in keys.items():
        txt += f"`{k}` ⏳ {duration_text(v)}\n"
    admin_bot.send_message(m.chat.id, txt, parse_mode="Markdown")

@admin_bot.message_handler(func=lambda m: m.chat.id in admin_logged and m.text == "🗑️ Delete Key")
def admin_del_prompt(m):
    admin_bot.send_message(m.chat.id, "Enter key to delete:")
    admin_bot.register_next_step_handler(m, admin_do_del)

def admin_do_del(m):
    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})
    if m.text in keys:
        del keys[m.text]
    for u in users.values():
        if u["key"] == m.text:
            u["deleted"] = True
    save(KEYS_FILE, keys)
    save(USERS_FILE, users)
    admin_bot.send_message(m.chat.id, "🗑️ Key deleted")
    show_admin_panel(m.chat.id)

@admin_bot.message_handler(func=lambda m: m.chat.id in admin_logged and m.text == "🚫 Block User")
def admin_block_prompt(m):
    admin_bot.send_message(m.chat.id, "Enter Telegram User ID:")
    admin_bot.register_next_step_handler(m, admin_do_block)

def admin_do_block(m):
    users = load(USERS_FILE, {})
    if m.text in users:
        users[m.text]["blocked"] = True
        save(USERS_FILE, users)
        admin_bot.send_message(m.chat.id, "🚫 User blocked")
    else:
        admin_bot.send_message(m.chat.id, "❌ User not found")
    show_admin_panel(m.chat.id)

@admin_bot.message_handler(func=lambda m: m.chat.id in admin_logged and m.text == "🚪 Logout")
def admin_logout(m):
    admin_logged.discard(m.chat.id)
    admin_bot.send_message(m.chat.id, "🚪 Logged out\n/start again")

# ================= THREADS =================
def run_user():
    print("✅ User bot running")
    user_bot.infinity_polling()

def run_admin():
    print("✅ Admin bot running")
    admin_bot.infinity_polling()

threading.Thread(target=run_user).start()
threading.Thread(target=run_admin).start()

while True:
    time.sleep(10)
