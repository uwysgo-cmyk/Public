import telebot
from telebot import types
import yt_dlp
import threading
import time
import re
import os
from datetime import datetime

# =========================
# إعدادات
TOKEN = os.getenv("TOKEN")
CHANNEL = "https://t.me/VideoExpressA"
TIKTOK_ACCOUNT = "https://www.tiktok.com/@a_max24"
DEVELOPER_ID = 7100818250

bot = telebot.TeleBot(TOKEN)

users = {}

# =========================
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
            'last_daily': None,
            'downloads': 0,
            'audios': 0
        }

# =========================
# 🎁 هدية يومية
def daily_points():
    while True:
        today = datetime.now().strftime("%Y-%m-%d")
        for uid in users:
            if users[uid]['last_daily'] != today:
                users[uid]['points'] += 1
                users[uid]['last_daily'] = today
                try:
                    bot.send_message(uid, "🎁 تم إضافة نقطة يومية!")
                except:
                    pass
        time.sleep(3600)

threading.Thread(target=daily_points, daemon=True).start()

# =========================
def is_url(text):
    return re.match(r'^https?://', text)

# =========================
# 🧠 حذف الملف بعد تأخير
def delete_later(file):
    time.sleep(120)  # دقيقتين
    if os.path.exists(file):
        os.remove(file)

# =========================
def send_file(uid, filename):
    try:
        with open(filename, "rb") as f:
            if filename.endswith(".mp3"):
                bot.send_audio(uid, f)
                users[uid]['audios'] += 1
            else:
                bot.send_video(uid, f)
                users[uid]['downloads'] += 1

        # حذف بعد تأخير
        threading.Thread(target=delete_later, args=(filename,)).start()

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ إرسال الملف: {str(e)}")

# =========================
# 🎬 تحميل من رابط
def download_media(url, uid, action):
    bot.send_message(uid, "⏳ جاري المعالجة...")

    ydl_opts = {
        'outtmpl': f'{uid}_%(title)s.%(ext)s',
        'noplaylist': True,
        'ffmpeg_location': '/usr/bin/ffmpeg'
    }

    if action == "📥 تحميل فيديو":
        ydl_opts['format'] = 'bestvideo+bestaudio/best'

    elif action == "🎵 استخراج صوت":
        bot.send_message(uid, "🎵 جاري استخراج الصوت...")
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }]
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if action == "🎵 استخراج صوت":
                filename = filename.rsplit('.', 1)[0] + ".mp3"

        users[uid]['points'] -= 1
        bot.send_message(uid, "✅ تم بنجاح، جاري الإرسال...")
        send_file(uid, filename)

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ: {str(e)}")

# =========================
@bot.message_handler(func=lambda m: True, content_types=['text','document'])
def handle(msg):
    uid = msg.from_user.id
    text = msg.text
    check_user(uid)

    if text == "↩️ رجوع":
        bot.send_message(uid, "🔙 رجوع", reply_markup=menu(uid))
        return

    if text == "👥 دعوة صديق":
        link = f"{CHANNEL}?start={uid}"
        bot.send_message(uid, f"رابطك:\n{link}")
        return

    if text == "🎯 تيكتوك":
        if not users[uid]['tiktok']:
            bot.send_message(uid, TIKTOK_ACCOUNT)
            users[uid]['points'] += 4
            users[uid]['tiktok'] = True
        return

    if text in ["📥 تحميل فيديو", "🎵 استخراج صوت"]:
        users[uid]['current_action'] = text
        bot.send_message(uid, "أرسل الرابط أو ملف فيديو")
        return

    # 👑 لوحة المطور
    if text == "👑 لوحة المطور" and uid == DEVELOPER_ID:
        total_users = len(users)
        total_points = sum(u['points'] for u in users.values())
        total_downloads = sum(u['downloads'] for u in users.values())
        total_audios = sum(u['audios'] for u in users.values())

        msg_stats = f"""
📊 إحصائيات:

👤 المستخدمين: {total_users}
💰 مجموع النقاط: {total_points}
🎬 تحميل فيديو: {total_downloads}
🎵 استخراج صوت: {total_audios}
"""
        bot.send_message(uid, msg_stats)
        return

    # 🔗 رابط
    if text and is_url(text):
        action = users[uid]['current_action']
        if not action:
            bot.send_message(uid, "❌ اختر العملية أولاً")
            return

        threading.Thread(target=download_media, args=(text, uid, action)).start()
        return

    # 📁 فيديو من الجهاز
    if msg.content_type == 'document':
        action = users[uid]['current_action']

        if action != "🎵 استخراج صوت":
            bot.send_message(uid, "❌ اختر استخراج صوت أولاً")
            return

        bot.send_message(uid, "⏳ جاري استخراج الصوت من الفيديو...")

        file_info = bot.get_file(msg.document.file_id)
        file = bot.download_file(file_info.file_path)

        filename = f"{uid}_video.mp4"
        with open(filename, "wb") as f:
            f.write(file)

        output = f"{uid}_audio.mp3"

        os.system(f"ffmpeg -i {filename} -vn -acodec libmp3lame {output}")

        send_file(uid, output)

        threading.Thread(target=delete_later, args=(filename,)).start()

# =========================
bot.polling()
