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
TOKEN = "8600251500:AAH1eo_1QzM4tTNPF2Vb_MxzYgkasMqK6CQ"
CHANNEL = "https://t.me/VideoExpressA"
TIKTOK_ACCOUNT = "https://www.tiktok.com/@a_max24"
DEVELOPER_ID = 7100818250

bot = telebot.TeleBot(TOKEN)
users = {}

# =========================
def menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 تحميل فيديو")
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
            'invites': 0
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
    time.sleep(120)
    if os.path.exists(file):
        os.remove(file)

# =========================
def send_file(uid, filename):
    try:
        with open(filename, "rb") as f:
            bot.send_video(uid, f)
            users[uid]['downloads'] += 1

        threading.Thread(target=delete_later, args=(filename,)).start()

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ إرسال الملف: {str(e)}")

# =========================
# 🎬 تحميل فيديو من رابط
def download_media(url, uid):
    bot.send_message(uid, "⏳ جاري المعالجة...")
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': f'{uid}_%(title)s.%(ext)s',
        'noplaylist': True,
        'ffmpeg_location': '/usr/bin/ffmpeg'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        users[uid]['points'] -= 1
        bot.send_message(uid, "✅ تم تحميل الفيديو، جاري الإرسال...")
        send_file(uid, filename)

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ: {str(e)}")

# =========================
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle(msg):
    uid = msg.from_user.id
    text = msg.text
    check_user(uid)

    # العودة للقائمة
    if text == "↩️ رجوع":
        bot.send_message(uid, "🔙 رجوع", reply_markup=menu(uid))
        users[uid]['current_action'] = None
        return

    # رابط الدعوة
    if text == "👥 دعوة صديق":
        link = f"{CHANNEL}?start={uid}"
        bot.send_message(uid, f"رابطك:\n{link}\n🔹 نقاطك: {users[uid]['points']}")
        return

    # تيك توك مع تأخير النقاط 7 ثوان
    if text == "🎯 تيكتوك":
        if not users[uid]['tiktok']:
            bot.send_message(uid, f"تابعنا على تيك توك: {TIKTOK_ACCOUNT}")
            
            def give_tiktok_points():
                time.sleep(7)
                users[uid]['points'] += 4
                users[uid]['tiktok'] = True
                bot.send_message(uid, "🎯 تم إضافة نقاط التيك توك لك!")
            
            threading.Thread(target=give_tiktok_points).start()
        else:
            bot.send_message(uid, "لقد حصلت على نقاط التيك توك مسبقًا!")
        return

    # تحميل الفيديو
    if text == "📥 تحميل فيديو":
        users[uid]['current_action'] = "download"
        bot.send_message(uid, "أرسل رابط الفيديو الآن:", reply_markup=types.ReplyKeyboardMarkup().add("↩️ رجوع"))
        return

    # لوحة المطور
    if text == "👑 لوحة المطور" and uid == DEVELOPER_ID:
        total_users = len(users)
        total_points = sum(u['points'] for u in users.values())
        total_downloads = sum(u['downloads'] for u in users.values())
        total_tiktok = sum(1 for u in users.values() if u['tiktok'])
        total_invites = sum(u['invites'] for u in users.values())

        # زر لإضافة نقاط للجميع
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("↩️ رجوع", "➕ إضافة نقاط للجميع")

        msg_stats = f"""
📊 إحصائيات المطور:

👤 المستخدمين: {total_users}
💰 مجموع النقاط: {total_points}
🎬 تحميل فيديو: {total_downloads}
🎯 نقاط تيك توك: {total_tiktok}
👥 الدعوات: {total_invites}
"""
        bot.send_message(uid, msg_stats, reply_markup=markup)
        return

    # إضافة نقاط للجميع
    if text == "➕ إضافة نقاط للجميع" and uid == DEVELOPER_ID:
        for u in users:
            users[u]['points'] += 5
        bot.send_message(uid, "✅ تم إضافة 5 نقاط لكل المستخدمين!")
        return

    # معالجة رابط الفيديو
    if text and is_url(text):
        if users[uid]['current_action'] == "download":
            threading.Thread(target=download_media, args=(text, uid)).start()
            return
        else:
            bot.send_message(uid, "❌ اختر العملية أولاً")
            return

bot.polling()
