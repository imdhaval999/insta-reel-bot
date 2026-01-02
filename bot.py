import telebot
import instaloader
import os
import shutil
import http.cookiejar as cookielib
from keep_alive import keep_alive

# 🔐 Telegram Bot Token (Render Environment)
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables")

bot = telebot.TeleBot(BOT_TOKEN)

# 🌐 Keep Render awake
keep_alive()

# 📥 Instaloader setup
L = instaloader.Instaloader(
    download_videos=True,
    download_video_thumbnails=False,
    download_comments=False,
    save_metadata=False,
    post_metadata_txt_pattern=""
)

# 🍪 Load Instagram cookies
cookiejar = cookielib.MozillaCookieJar("cookies.txt")
cookiejar.load(ignore_discard=True, ignore_expires=True)
L.context._session.cookies = cookiejar

DOWNLOAD_DIR = "downloads"

# ▶️ Start command
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Welcome!\n\n"
        "🎥 Send any Instagram Reel link\n"
        "⬇️ Get video with original caption\n\n"
        "⚡ Fast • Clean • Pro Output"
    )

# 🎬 Reel handler
@bot.message_handler(func=lambda m: m.text and "instagram.com/reel" in m.text)
def download_reel(message):
    try:
        url = message.text.strip()
        shortcode = url.split("/")[-2]

        status = bot.send_message(
            message.chat.id,
            "⏳ Downloading reel… please wait"
        )

        post = instaloader.Post.from_shortcode(L.context, shortcode)

        # Prepare download folder
        if os.path.exists(DOWNLOAD_DIR):
            shutil.rmtree(DOWNLOAD_DIR)
        os.mkdir(DOWNLOAD_DIR)

        L.download_post(post, target=DOWNLOAD_DIR)

        # 📌 Caption exactly like Instagram style
        insta_caption = post.caption or ""
        insta_caption = insta_caption.strip()[:1000]

        final_caption = insta_caption  # RAW caption (no markdown)

        # 🎥 Send video (preview style)
        sent = False
        for file in os.listdir(DOWNLOAD_DIR):
            if file.endswith(".mp4"):
                with open(os.path.join(DOWNLOAD_DIR, file), "rb") as video:
                    bot.send_video(
                        message.chat.id,
                        video,
                        caption=final_caption
                    )
                sent = True
                break

        shutil.rmtree(DOWNLOAD_DIR)
        bot.delete_message(message.chat.id, status.message_id)

        if not sent:
            bot.send_message(message.chat.id, "❌ Video not found")

    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ Failed to download reel\n\n"
            "Possible reasons:\n"
            "• Private reel\n"
            "• Invalid link\n"
            "• Cookies expired"
        )

print("✅ Pro Reel Bot is running (Video only)…")
bot.polling(non_stop=True)
