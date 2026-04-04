import telebot
from telebot import types
import yt_dlp
import threading
import time
import re
import os

# =========================
# إعدادات البوت
TOKEN = "PUT_YOUR_TOKEN_HERE"
CHANNEL = "https://t.me/VideoExpressA"
TIKTOK_ACCOUNT = "https://www.tiktok.com/@a_max24"
DEVELOPER_ID = 7100818250

bot = telebot.TeleBot(TOKEN)

# =========================
# قاعدة بيانات المستخدمين
users = {}

# =========================
# قائمة
def menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 تحميل فيديو", "🎵 استخراج صوت")
    markup.add("👥 دعوة صديق", "🎯 تيكتوك")
    if uid == DEVELOPER_ID:
        markup.add("👑 لوحة المطور")
    return markup

# =========================
def check_user(uid):
    if uid not in users:
        users[uid] = {
            'points': 5,
            'tiktok': False,
            'current_action': None,
            'daily': 0
        }

# =========================
# هدية يومية (كل 24 ساعة)
def daily_reward(uid):
    now = time.time()
    if now - users[uid]['daily'] > 86400:
        users[uid]['points'] += 1
        users[uid]['daily'] = now
        bot.send_message(uid, f"🎁 حصلت على نقطة يومية!\n🔹 نقاطك: {users[uid]['points']}")

# =========================
def is_url(text):
    return re.match(r'^https?://', text)

# =========================
# إرسال ملف
def send_file(uid, filename):
    try:
        with open(filename, "rb") as f:
            if filename.endswith(".mp3"):
                bot.send_audio(uid, f)
            else:
                bot.send_video(uid, f)
        os.remove(filename)
    except Exception as e:
        bot.send_message(uid, f"❌ خطأ في الإرسال: {str(e)}")

# =========================
# استخراج صوت من فيديو مرفوع
def extract_audio_from_file(uid, file_id):
    try:
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)

        video_name = f"{uid}_input.mp4"
        with open(video_name, "wb") as f:
            f.write(downloaded)

        audio_name = f"{uid}_audio.mp3"

        os.system(f"ffmpeg -i {video_name} -vn -ab 192k {audio_name}")

        bot.send_audio(uid, open(audio_name, "rb"))

        os.remove(video_name)
        os.remove(audio_name)

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ في تحويل الفيديو: {str(e)}")

# =========================
@bot.message_handler(content_types=['video'])
def handle_video(msg):
    uid = msg.from_user.id
    check_user(uid)

    if users[uid]['current_action'] == "🎵 استخراج صوت":
        bot.send_message(uid, "⏳ جاري استخراج الصوت...")
        threading.Thread(target=extract_audio_from_file, args=(uid, msg.video.file_id)).start()

# =========================
@bot.message_handler(func=lambda m: True)
def handle(msg):
    uid = msg.from_user.id
    text = msg.text
    check_user(uid)
    daily_reward(uid)

    if text == "↩️ رجوع":
        bot.send_message(uid, "🔙 رجعت", reply_markup=menu(uid))
        users[uid]['current_action'] = None
        return

    if text == "👥 دعوة صديق":
        bot.send_message(uid, f"رابطك:\n{CHANNEL}?start={uid}")
        return

    if text == "🎯 تيكتوك":
        if not users[uid]['tiktok']:
            bot.send_message(uid, TIKTOK_ACCOUNT)
            users[uid]['points'] += 4
            users[uid]['tiktok'] = True
        else:
            bot.send_message(uid, "❌ استعملتها سابقاً")
        return

    if text in ["📥 تحميل فيديو", "🎵 استخراج صوت"]:
        users[uid]['current_action'] = text
        bot.send_message(uid, "📩 أرسل الرابط أو الفيديو")
        return

    if text and is_url(text):
        action = users[uid]['current_action']
        if not action:
            bot.send_message(uid, "❌ اختر العملية أولاً", reply_markup=menu(uid))
            return

        ydl_opts = {
            'outtmpl': f'{uid}_%(title).50s.%(ext)s',
            'noplaylist': True,
            'ffmpeg_location': '/usr/bin/ffmpeg',

            # 🔥 حل Instagram
            'cookiefile': 'cookies.txt',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0'
            }
        }

        if action == "📥 تحميل فيديو":
            ydl_opts['format'] = 'best'
        else:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=True)
                filename = ydl.prepare_filename(info)

                if action == "🎵 استخراج صوت":
                    filename = filename.rsplit('.', 1)[0] + ".mp3"

            bot.send_message(uid, "✅ تم التحميل، جاري الإرسال...")
            threading.Thread(target=send_file, args=(uid, filename)).start()

        except Exception as e:
            bot.send_message(uid, f"❌ خطأ: {str(e)}")

        users[uid]['current_action'] = None
        return

    bot.send_message(uid, "❌ أمر غير صالح", reply_markup=menu(uid))

# =========================
bot.polling()
