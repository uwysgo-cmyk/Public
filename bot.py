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
TOKEN = os.getenv("TOKEN")  # متغير البيئة للتوكن
CHANNEL = "@VideoExpressA"
TIKTOK_ACCOUNT = "https://www.tiktok.com/@a_max24"
DEVELOPER_ID = 7100818250

bot = telebot.TeleBot(TOKEN)
users = {}

# =========================
def menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 تحميل فيديو", "👥 دعوة صديق", "🎯 تيكتوك")
    if uid == DEVELOPER_ID:
        markup.add("👑 لوحة المطور")
    markup.add("↩️ رجوع")
    return markup

# =========================
def check_user(uid):
    if uid not in users:
        users[uid] = {
            'points': 3,  # الرصيد الابتدائي
            'tiktok': False,
            'current_action': None,
            'last_daily': None,
            'downloads': 0,
            'audios': 0
        }

# =========================
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
def delete_later(file):
    time.sleep(120)
    if os.path.exists(file):
        os.remove(file)

# =========================
def send_file(uid, filename):
    if users[uid]['points'] <= 0:
        bot.send_message(uid, "❌ رصيدك انتهى، يرجى زيادة النقاط!")
        return

    try:
        with open(filename, "rb") as f:
            bot.send_video(uid, f)
            users[uid]['downloads'] += 1
            users[uid]['points'] -= 1

        bot.send_message(uid, f"✅ تم الإرسال بنجاح!\n💰 رصيدك الحالي: {users[uid]['points']} نقاط")

        threading.Thread(target=delete_later, args=(filename,)).start()

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ إرسال الملف: {str(e)}")

# =========================
def download_media(url, uid):
    if users[uid]['points'] <= 0:
        bot.send_message(uid, "❌ رصيدك انتهى، يرجى زيادة النقاط!")
        return

    bot.send_message(uid, "⏳ جاري التحميل...")

    ydl_opts = {
        'outtmpl': f'{uid}_%(title)s.%(ext)s',
        'noplaylist': True,
        'ffmpeg_location': '/usr/bin/ffmpeg'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        users[uid]['points'] -= 1
        bot.send_message(uid, f"✅ تم التحميل بنجاح!\n💰 رصيدك الحالي: {users[uid]['points']} نقاط")
        send_file(uid, filename)

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ: {str(e)}")

# =========================
@bot.message_handler(func=lambda m: True, content_types=['text','document'])
def handle(msg):
    uid = msg.from_user.id
    text = msg.text
    check_user(uid)

    # زر رجوع
    if text == "↩️ رجوع":
        users[uid]['current_action'] = None
        bot.send_message(uid, "🔙 تم الرجوع", reply_markup=menu(uid))
        return

    # دعوة صديق
    if text == "👥 دعوة صديق":
        users[uid]['points'] += 3
        link = f"{CHANNEL}?start={uid}"
        bot.send_message(uid, f"رابطك:\n{link}\n💰 رصيدك الحالي: {users[uid]['points']} نقاط")
        return

    # تيكتوك
    if text == "🎯 تيكتوك":
        if not users[uid]['tiktok']:
            bot.send_message(uid, TIKTOK_ACCOUNT)
            users[uid]['points'] += 4
            users[uid]['tiktok'] = True
            bot.send_message(uid, f"💰 حصلت على 4 نقاط!\n💰 رصيدك الحالي: {users[uid]['points']} نقاط")
        return

    # تحميل فيديو
    if text == "📥 تحميل فيديو":
        users[uid]['current_action'] = "download"
        bot.send_message(uid, "📎 أرسل رابط الفيديو")
        return

    # لوحة المطور
    if text == "👑 لوحة المطور" and uid == DEVELOPER_ID:
        total_users = len(users)
        total_points = sum(u['points'] for u in users.values())
        total_downloads = sum(u['downloads'] for u in users.values())

        msg_stats = f"""
📊 إحصائيات البوت:

👤 المستخدمين: {total_users}
💰 مجموع النقاط: {total_points}
🎬 تحميل فيديو: {total_downloads}
"""
        bot.send_message(uid, msg_stats)

        # إضافة نقاط لجميع المستخدمين
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ إضافة نقاط للجميع", "↩️ رجوع")
        bot.send_message(uid, "اختر إجراء:", reply_markup=markup)
        return

    # إضافة نقاط لجميع المستخدمين (لوحة المطور)
    if text == "➕ إضافة نقاط للجميع" and uid == DEVELOPER_ID:
        for u in users:
            users[u]['points'] += 1
        bot.send_message(uid, "✅ تم إضافة نقطة لكل المستخدمين!")
        return

    # رابط لتحميل الفيديو
    if text and is_url(text):
        if users[uid]['current_action'] != "download":
            bot.send_message(uid, "❌ يرجى اختيار عملية أولاً")
            return
        threading.Thread(target=download_media, args=(text, uid)).start()
        return

    # إدخال غير صالح
    if text and not is_url(text):
        bot.send_message(uid, "❌ هذا ليس رابطاً صالحاً.")

# =========================
bot.polling()
