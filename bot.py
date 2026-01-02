import telebot, os, json, time, random, string, shutil
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

def duration_text(sec):
    if sec < 3600:
        return f"{sec//60} Minutes"
    if sec < 86400:
        return "1 Day"
    return "30 Days"

def user_active(uid):
    users = load(USERS_FILE, {})
    return str(uid) in users and time.time() < users[str(uid)]["expire"]

def ensure_sales():
    if not os.path.exists(SALES_FILE):
        save(SALES_FILE, {
            "total_generated": 0,
            "total_sold": 0,
            "total_downloads": 0
        })

# ================= INSTAGRAM =================
L = instaloader.Instaloader(download_videos=True, save_metadata=False)
cj = cookielib.MozillaCookieJar("cookies.txt")
cj.load(ignore_discard=True, ignore_expires=True)
L.context._session.cookies = cj
DOWNLOAD_DIR = "downloads"

# ================= START =================
def send_welcome(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👑 Owner Login")
    bot.send_message(
        cid,
        "🔥 *Instagram Reel Downloader – Private Bot*\n\n"
        "🔐 Enter your key to start service\n"
        "💬 Buy key 👉 @imvrct",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["start"])
def start(m):
    admin_sessions.discard(m.chat.id)
    admin_waiting.discard(m.chat.id)
    send_welcome(m.chat.id)

# ================= OWNER LOGIN =================
@bot.message_handler(func=lambda m: m.text == "👑 Owner Login")
def owner_login(m):
    admin_waiting.add(m.chat.id)
    bot.send_message(m.chat.id, "👋 Welcome Owner\n🔐 Enter admin key")

@bot.message_handler(func=lambda m: m.chat.id in admin_waiting)
def admin_key_loop(m):
    if m.text.strip() != ADMIN_SECRET:
        bot.send_message(m.chat.id, "❌ Key not found\n🔁 Try again")
        return
    admin_waiting.discard(m.chat.id)
    admin_sessions.add(m.chat.id)
    show_admin_panel(m.chat.id)

# ================= ADMIN PANEL =================
def admin_only(m):
    if m.chat.id not in admin_sessions:
        bot.send_message(m.chat.id, "🔐 Please login as admin")
        return False
    return True

def show_admin_panel(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Generate Key", "🔁 Renew User")
    kb.add("📋 All Keys", "📊 Sales & Usage")
    kb.add("❌ Delete Key", "🚪 Logout")
    bot.send_message(cid, "👑 *Admin Panel*", reply_markup=kb, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Generate Key")
def gen_key_menu(m):
    if not admin_only(m): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5 Minutes", "1 Day", "30 Days")
    bot.send_message(m.chat.id, "⏳ Select duration", reply_markup=kb)

@bot.message_handler(func=lambda m: m.chat.id in admin_sessions and m.text in ["5 Minutes","1 Day","30 Days"])
def do_gen_key(m):
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
        f"✅ *Key Generated*\n\n🔑 `{key}`\n⏳ {m.text}",
        parse_mode="Markdown"
    )
    show_admin_panel(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "🔁 Renew User")
def renew_prompt(m):
    if not admin_only(m): return
    bot.send_message(m.chat.id, "Send Telegram User ID:")
    bot.register_next_step_handler(m, renew_user)

def renew_user(m):
    if not admin_only(m): return
    uid = m.text.strip()
    users = load(USERS_FILE, {})
    if uid not in users:
        bot.send_message(m.chat.id, "❌ User not found")
        show_admin_panel(m.chat.id)
        return
    users[uid]["expire"] += 86400
    save(USERS_FILE, users)
    bot.send_message(m.chat.id, "✅ User renewed for 1 Day")
    show_admin_panel(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "📊 Sales & Usage")
def stats(m):
    if not admin_only(m): return
    ensure_sales()
    sales = load(SALES_FILE, {})
    users = load(USERS_FILE, {})
    txt = (
        f"📊 *Sales & Usage Stats*\n\n"
        f"🔑 Keys Generated: {sales['total_generated']}\n"
        f"💰 Keys Sold: {sales['total_sold']}\n"
        f"👤 Active Users: {len(users)}\n"
        f"🎬 Total Downloads: {sales['total_downloads']}"
    )
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "❌ Delete Key")
def del_key_prompt(m):
    if not admin_only(m): return
    bot.send_message(m.chat.id, "Enter key to delete:")
    bot.register_next_step_handler(m, do_del_key)

def do_del_key(m):
    if not admin_only(m): return
    keys = load(KEYS_FILE, {})
    if m.text in keys:
        del keys[m.text]
        save(KEYS_FILE, keys)
        bot.send_message(m.chat.id, "✅ Key deleted")
    else:
        bot.send_message(m.chat.id, "❌ Key not found")
    show_admin_panel(m.chat.id)

@bot.message_handler(func=lambda m: m.text == "🚪 Logout")
def logout(m):
    admin_sessions.discard(m.chat.id)
    admin_waiting.discard(m.chat.id)
    bot.send_message(m.chat.id, "🚪 Logged out successfully")
    send_welcome(m.chat.id)

# ================= USER KEY =================
@bot.message_handler(func=lambda m: m.text.startswith("imdhaval-"))
def user_key(m):
    bot.send_message(m.chat.id, "⏳ Checking your key...")
    keys = load(KEYS_FILE, {})
    users = load(USERS_FILE, {})
    sales = load(SALES_FILE, {})

    if m.text not in keys:
        bot.send_message(m.chat.id, "❌ Wrong key\n🔁 Try again\n💬 @imvrct")
        return

    users[str(m.chat.id)] = {
        "expire": time.time() + keys[m.text],
        "downloads": 0,
        "last_used": None
    }
    del keys[m.text]
    save(KEYS_FILE, keys)
    save(USERS_FILE, users)

    sales["total_sold"] += 1
    save(SALES_FILE, sales)

    bot.send_message(
        m.chat.id,
        f"✅ Successfully Logged In 🎉\n⏳ Duration: {duration_text(86400)}\n👇 Enter reel link 🎬"
    )

# ================= REEL =================
@bot.message_handler(func=lambda m: "instagram.com/reel" in m.text)
def reel(m):
    if not user_active(m.chat.id):
        bot.send_message(m.chat.id, "⏰ Key expired\n🔐 Enter new key")
        return

    users = load(USERS_FILE, {})
    sales = load(SALES_FILE, {})
    users[str(m.chat.id)]["downloads"] += 1
    users[str(m.chat.id)]["last_used"] = int(time.time())
    sales["total_downloads"] += 1
    save(USERS_FILE, users)
    save(SALES_FILE, sales)

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

print("✅ Professional Paid Reel Bot Running…")
bot.polling(non_stop=True)
