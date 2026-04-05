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
CHANNEL = "@VideoExpressA"  # استخدم معرف القناة لا الرابط الكامل
TIKTOK_ACCOUNT = "https://www.tiktok.com/@a_max24"
DEVELOPER_ID = 7100818250

bot = telebot.TeleBot(TOKEN)
users = {}

# =========================
# قائمة رئيسية
def menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 تحميل فيديو")
    markup.add("👥 دعوة صديق", "🎯 تيكتوك")
    if uid == DEVELOPER_ID:
        markup.add("👑 لوحة المطور")
    return markup

# =========================
# تحقق من العضوية في القناة
def check_membership(uid):
    try:
        member = bot.get_chat_member(CHANNEL, uid)
        if member.status in ['left', 'kicked']:
            bot.send_message(uid, "❌ يجب الانضمام للقناة أولاً")
            return False
        return True
    except:
        bot.send_message(uid, "❌ تعذر التحقق من الانضمام للقناة")
        return False

# =========================
# التحقق من وجود المستخدم
def check_user(uid):
    if uid not in users:
        users[uid] = {
            'points': 3,  # الرصيد الأولي 3
            'tiktok': False,
            'current_action': None,
            'last_daily': None,
            'downloads': 0,
            'audios': 0
        }

# =========================
# هدية يومية
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
# حذف الملف بعد تأخير
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
        bot.send_message(uid, f"✅ تم الإرسال! رصيدك الحالي: {users[uid]['points']} نقاط")
    except Exception as e:
        bot.send_message(uid, f"❌ خطأ إرسال الملف: {str(e)}")

# =========================
# تحميل من رابط
def download_media(url, uid):
    if users[uid]['points'] <= 0:
        bot.send_message(uid, "❌ رصيدك انتهى! شارك أو تابع تيكتوك للحصول على نقاط")
        return

    bot.send_message(uid, "⏳ جاري المعالجة...")
    ydl_opts = {
        'outtmpl': f'{uid}_%(title)s.%(ext)s',
        'noplaylist': True,
        'ffmpeg_location': '/usr/bin/ffmpeg',
        'format': 'bestvideo+bestaudio/best'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        users[uid]['points'] -= 1
        send_file(uid, filename)

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ: {str(e)}")

# =========================
@bot.message_handler(func=lambda m: True, content_types=['text','document'])
def handle(msg):
    uid = msg.from_user.id
    text = msg.text
    check_user(uid)

    # تحقق من العضوية قبل أي عملية
    if not check_membership(uid):
        return

    if text == "↩️ رجوع":
        bot.send_message(uid, "🔙 رجوع", reply_markup=menu(uid))
        return

    if text == "👥 دعوة صديق":
        users[uid]['points'] += 3
        link = f"{CHANNEL}?start={uid}"
        bot.send_message(uid, f"رابطك:\n{link}\n✅ تم إضافة 3 نقاط لرصيدك\nرصيدك الحالي: {users[uid]['points']}")
        return

    if text == "🎯 تيكتوك":
        if not users[uid]['tiktok']:
            bot.send_message(uid, TIKTOK_ACCOUNT)
            users[uid]['points'] += 4
            users[uid]['tiktok'] = True
            bot.send_message(uid, f"✅ تم إضافة 4 نقاط لرصيدك\nرصيدك الحالي: {users[uid]['points']}")
        return

    if text == "📥 تحميل فيديو":
        users[uid]['current_action'] = text
        bot.send_message(uid, "أرسل الرابط")
        return

    # لوحة المطور
    if text == "👑 لوحة المطور" and uid == DEVELOPER_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("إضافة نقاط للجميع", "↩️ رجوع")
        bot.send_message(uid, "👑 لوحة المطور", reply_markup=markup)
        return

    # إضافة نقاط للجميع (لوحة المطور)
    if text == "إضافة نقاط للجميع" and uid == DEVELOPER_ID:
        for u in users:
            users[u]['points'] += 1
        bot.send_message(uid, "✅ تم إضافة 1 نقطة لكل المستخدمين")
        return

    # رابط
    if text and is_url(text):
        action = users[uid]['current_action']
        if not action:
            bot.send_message(uid, "❌ اختر العملية أولاً")
            return
        threading.Thread(target=download_media, args=(text, uid)).start()
        return

# =========================
bot.polling()
