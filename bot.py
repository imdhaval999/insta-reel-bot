import telebot
import instaloader
import os
import shutil
import http.cookiejar as cookielib
from keep_alive import keep_alive

# 🔐 Token from Render Environment
BOT_TOKEN = os.getenv("8208876135:AAGm9nOwTcyqR2WFNH-174PKecmUISKlS20")

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

# 🍪 Load cookies.txt
cookiejar = cookielib.MozillaCookieJar("cookies.txt")
cookiejar.load(ignore_discard=True, ignore_expires=True)
L.context._session.cookies = cookiejar

DOWNLOAD_DIR = "downloads"

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 *Welcome to Pro Instagram Reel Downloader*\n\n"
        "🎥 Send any Instagram Reel link\n"
        "⚡ Get HD video instantly\n\n"
        "✨ *Video Only • Clean • Fast*",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text and "instagram.com/reel" in m.text)
def download_reel(message):
    try:
        url = message.text.strip()
        shortcode = url.split("/")[-2]

        status = bot.send_message(
            message.chat.id,
            "⏳ *Downloading your reel…*\nPlease wait ⌛",
            parse_mode="Markdown"
        )

        post = instaloader.Post.from_shortcode(L.context, shortcode)

        if os.path.exists(DOWNLOAD_DIR):
            shutil.rmtree(DOWNLOAD_DIR)
        os.mkdir(DOWNLOAD_DIR)

        L.download_post(post, target=DOWNLOAD_DIR)

        caption_text = post.caption or "No caption available"
        caption_text = caption_text[:900]

        final_caption = (
            "🎬 *Instagram Reel*\n\n"
            f"📝 *Title:*\n{caption_text}\n\n"
            "🚀 _Downloaded via Pro Reel Bot_"
        )

        sent = False
        for file in os.listdir(DOWNLOAD_DIR):
            if file.endswith(".mp4"):
                with open(os.path.join(DOWNLOAD_DIR, file), "rb") as video:
                    bot.send_video(
                        message.chat.id,
                        video,
                        caption=final_caption,
                        parse_mode="Markdown"
                    )
                sent = True
                break

        shutil.rmtree(DOWNLOAD_DIR)
        bot.delete_message(message.chat.id, status.message_id)

        if not sent:
            bot.send_message(message.chat.id, "❌ Video not found.")

    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ *Failed to download reel*\n\n"
            "⚠️ Possible reasons:\n"
            "• Private reel\n"
            "• Invalid link\n"
            "• Cookies expired",
            parse_mode="Markdown"
        )

print("✅ Render Video-Only Reel Bot is running…")
bot.polling(non_stop=True)
