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

admin_wait = set()      # admin waiting for key
admin_live = set()      # admin logged in
user_logged = set()     # user logged in
admin_gen_state = {}   # temp state for key generation

# ================= HELPERS =================
def load(f, d):
    if not os.path.exists(f):
        return d
    return json.load(open(f))

def save(f, d):
    json.dump(d, open(f, "w"), indent=2)

def duration_txt(sec):
    if sec <= 0:
        return "Expired"
    m = sec // 60
    if m < 60:
        return f"{m} Min"
    h = m // 60
    if h < 24:
        return f"{h} Hr"
    return f"{h//24} Day"

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

def show_user_service(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔑 My Key")
    bot.send_message(
        cid,
        "✅ *Service Activated*\n\n🎬 Send Instagram Reel link",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    admin_wait.discard(m.chat.id)
    admin_live.discard(m.chat.id)
    user_welcome(m.chat.id)

# ================= USER KEY LOGIN =================
@bot.message_handler(func=lambda m: m.text and m.text.startswith("imdhaval-") and m.chat.id not in admin_live)
def user_key(m):
    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})

    if m.text not in keys:
        bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")
        return

    key_data = keys[m.text]

    # single-user check
    if key_data["type"] == "single" and key_data["used_by"]:
        bot.send_message(m.chat.id, "🚫 This key already used")
        return

    users[str(m.chat.id)] = {
        "key": m.text,
        "expire": time.time() + key_data["duration"],
        "blocked": False,
        "deleted": False
    }

    key_data["used_by"].append(m.chat.id)
    save(KEYS_FILE, keys)
    save(USERS_FILE, users)

    user_logged.add(m.chat.id)
    bot.send_message(m.chat.id, "✅ *Successfully Logged In* 🎉", parse_mode="Markdown")
    show_user_service(m.chat.id)

# ================= MY KEY =================
@bot.message_handler(func=lambda m: m.text == "🔑 My Key" and m.chat.id in user_logged and m.chat.id not in admin_live)
def my_key(m):
    status, u = user_status(m.chat.id)
    if status != "active":
        user_logged.discard(m.chat.id)
        bot.send_message(m.chat.id, "⚠️ Key not active\n🔐 Enter new key")
        return

    bot.send_message(
        m.chat.id,
        f"🔑 *Your Key*\n\n"
        f"📌 Status: Active\n"
        f"⏳ Time Left: {duration_txt(int(u['expire']-time.time()))}",
        parse_mode="Markdown"
    )

# ================= REEL DOWNLOAD =================
@bot.message_handler(func=lambda m: "instagram.com/reel" in m.text and m.chat.id not in admin_live)
def reel(m):
    status, _ = user_status(m.chat.id)
    if status != "active":
        bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")
        return

    try:
        shortcode = m.text.split("/")[-2]
        msg = bot.send_message(m.chat.id, "⏳ Downloading reel…")

        post = instaloader.Post.from_shortcode(L.context, shortcode)

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
        "👑 *Welcome to Admin Panel*\n\n🔐 Enter admin key",
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
    kb.add("➕ Generate Key")
    kb.add("📂 Manage Keys")
    kb.add("🚪 Logout")
    bot.send_message(cid, "👑 *Admin Panel*", reply_markup=kb, parse_mode="Markdown")

def admin_only(m):
    if m.chat.id not in admin_live:
        bot.send_message(m.chat.id, "🔐 Login as Admin")
        return False
    return True

@bot.message_handler(func=lambda m: m.text == "🚪 Logout")
def admin_logout(m):
    admin_live.discard(m.chat.id)
    user_welcome(m.chat.id)

# ================= GENERATE KEY =================
@bot.message_handler(func=lambda m: m.text == "➕ Generate Key")
def gen_type(m):
    if not admin_only(m): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Single User", "Multi User")
    bot.send_message(m.chat.id, "Select key type", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_live and m.text in ["Single User","Multi User"])
def gen_duration(m):
    admin_gen_state[m.chat.id] = {
        "type": "single" if m.text == "Single User" else "multi"
    }
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 Min", "1 Day", "30 Day")
    bot.send_message(m.chat.id, "Select duration", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_live and m.text in ["5 Min","1 Day","30 Day"])
def gen_key(m):
    if m.chat.id not in admin_gen_state:
        bot.send_message(m.chat.id, "⚠️ Start from Generate Key")
        return

    duration_map = {"5 Min":300,"1 Day":86400,"30 Day":2592000}
    key = "imdhaval-" + str(int(time.time()))

    keys = load(KEYS_FILE, {})
    keys[key] = {
        "duration": duration_map[m.text],
        "type": admin_gen_state[m.chat.id]["type"],
        "used_by": []
    }
    save(KEYS_FILE, keys)
    del admin_gen_state[m.chat.id]

    bot.send_message(
        m.chat.id,
        f"✅ *Key Generated*\n\n"
        f"🔑 `{key}`\n"
        f"👥 Type: {keys[key]['type']}\n"
        f"⏳ {m.text}",
        parse_mode="Markdown"
    )
    show_admin_panel(m.chat.id)

# ================= MANAGE KEYS =================
@bot.message_handler(func=lambda m: m.text == "📂 Manage Keys")
def manage_keys(m):
    if not admin_only(m): return
    keys = load(KEYS_FILE, {})
    if not keys:
        bot.send_message(m.chat.id, "No keys found")
        return

    msg = "📂 *All Keys*\n\n"
    for k,v in keys.items():
        msg += (
            f"🔑 `{k}`\n"
            f"👥 Type: {v['type']}\n"
            f"⏳ {duration_txt(v['duration'])}\n"
            f"👤 Used: {len(v['used_by'])}\n"
            f"➡️ delete {k}\n"
            f"➡️ extend {k}\n\n"
        )
    bot.send_message(m.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text.startswith("delete "))
def delete_key(m):
    if not admin_only(m): return
    key = m.text.replace("delete ","")
    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})

    if key in keys:
        del keys[key]

    for u in users.values():
        if u["key"] == key:
            u["deleted"] = True

    save(KEYS_FILE, keys)
    save(USERS_FILE, users)
    bot.send_message(m.chat.id, "🗑️ Key deleted")

@bot.message_handler(func=lambda m: m.text.startswith("extend "))
def extend_key(m):
    if not admin_only(m): return
    key = m.text.replace("extend ","")
    keys = load(KEYS_FILE, {})
    if key in keys:
        keys[key]["duration"] += 86400
        save(KEYS_FILE, keys)
        bot.send_message(m.chat.id, "⏳ Key extended by 1 Day")

# ================= FALLBACK =================
@bot.message_handler(func=lambda m: True)
def fallback(m):
    if m.text != "/start":
        bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")

print("✅ FINAL Single Bot Running (User + Admin + Reel Service)…")
bot.polling(non_stop=True)
