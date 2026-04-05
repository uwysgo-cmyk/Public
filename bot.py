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
TOKEN = os.getenv("TOKEN")  # في Railway، اضبط TOKEN كمتغير بيئة
CHANNEL = "https://t.me/VideoExpressA"
TIKTOK_ACCOUNT = "https://www.tiktok.com/@a_max24"
DEVELOPER_ID = 7100818250

bot = telebot.TeleBot(TOKEN)

users = {}

# =========================
# إعداد قائمة المستخدم
def menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 تحميل فيديو", "👥 دعوة صديق", "🎯 تيكتوك")
    if uid == DEVELOPER_ID:
        markup.add("👑 لوحة المطور")
    markup.add("↩️ رجوع")
    return markup

# =========================
# التحقق من المستخدم
def check_user(uid):
    if uid not in users:
        users[uid] = {
            'points': 3,        # رصيد افتراضي
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
# حذف الملفات بعد الإرسال
def delete_later(file):
    time.sleep(120)
    if os.path.exists(file):
        os.remove(file)

# =========================
# إرسال الملفات مع تحديث الرصيد
def send_file(uid, filename):
    try:
        if users[uid]['points'] <= 0:
            bot.send_message(uid, "❌ رصيدك انتهى، يرجى إضافة نقاط.")
            return

        with open(filename, "rb") as f:
            if filename.endswith(".mp3"):
                bot.send_audio(uid, f)
                users[uid]['audios'] += 1
            else:
                bot.send_video(uid, f)
                users[uid]['downloads'] += 1

        users[uid]['points'] -= 1
        bot.send_message(uid, f"✅ تم الإرسال بنجاح، رصيدك الحالي: {users[uid]['points']} نقطة")
        threading.Thread(target=delete_later, args=(filename,)).start()

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ إرسال الملف: {str(e)}")

# =========================
# تحميل من رابط
def download_media(url, uid):
    if users[uid]['points'] <= 0:
        bot.send_message(uid, "❌ رصيدك انتهى، يرجى إضافة نقاط.")
        return

    bot.send_message(uid, "⏳ جاري المعالجة...")

    ydl_opts = {
        'outtmpl': f'{uid}_%(title)s.%(ext)s',
        'noplaylist': True,
        'ffmpeg_location': '/usr/bin/ffmpeg'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        send_file(uid, filename)

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ: {str(e)}")

# =========================
# التحقق من الانضمام للقناة
def check_membership(uid):
    try:
        member = bot.get_chat_member(chat_id=CHANNEL, user_id=uid)
        if member.status in ['left', 'kicked']:
            bot.send_message(uid, "❌ يجب أن تكون عضوًا في القناة لاستخدام البوت.")
            return False
        return True
    except:
        bot.send_message(uid, "❌ تعذر التحقق من العضوية. تأكد من القناة.")
        return False

# =========================
@bot.message_handler(func=lambda m: True, content_types=['text','document'])
def handle(msg):
    uid = msg.from_user.id
    text = msg.text
    check_user(uid)

    if not check_membership(uid):
        return

    # رجوع
    if text == "↩️ رجوع":
        bot.send_message(uid, "🔙 رجوع", reply_markup=menu(uid))
        return

    # دعوة صديق
    if text == "👥 دعوة صديق":
        link = f"{CHANNEL}?start={uid}"
        users[uid]['points'] += 3
        bot.send_message(uid, f"رابطك:\n{link}\n✅ تمت إضافة 3 نقاط، رصيدك الآن: {users[uid]['points']}")
        return

    # تيكتوك
    if text == "🎯 تيكتوك":
        if not users[uid]['tiktok']:
            users[uid]['points'] += 4
            users[uid]['tiktok'] = True
            bot.send_message(uid, f"{TIKTOK_ACCOUNT}\n✅ تمت إضافة 4 نقاط، رصيدك الآن: {users[uid]['points']}")
        else:
            bot.send_message(uid, f"✅ سبق وأن ضغطت رابط التيكتوك، رصيدك: {users[uid]['points']}")
        return

    # تحميل فيديو
    if text == "📥 تحميل فيديو":
        users[uid]['current_action'] = "download"
        bot.send_message(uid, "أرسل رابط الفيديو")
        return

    # لوحة المطور
    if text == "👑 لوحة المطور" and uid == DEVELOPER_ID:
        msg_stats = f"""
📊 إحصائيات:

👤 المستخدمين: {len(users)}
💰 مجموع النقاط: {sum(u['points'] for u in users.values())}
🎬 تحميل فيديو: {sum(u['downloads'] for u in users.values())}
"""
        bot.send_message(uid, msg_stats)

        # خيار إضافة نقاط لجميع المستخدمين
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ إضافة نقاط للجميع", "↩️ رجوع")
        bot.send_message(uid, "اختر الإجراء:", reply_markup=markup)
        return

    # إضافة نقاط للجميع (لوحة المطور)
    if text == "➕ إضافة نقاط للجميع" and uid == DEVELOPER_ID:
        for u in users:
            users[u]['points'] += 3
        bot.send_message(uid, "✅ تمت إضافة 3 نقاط لجميع المستخدمين")
        return

    # 🔗 رابط الفيديو
    if text and is_url(text):
        if users[uid]['current_action'] != "download":
            bot.send_message(uid, "❌ اختر العملية أولاً")
            return
        threading.Thread(target=download_media, args=(text, uid)).start()
        return

    # أي شيء غير رابط
    if text and not is_url(text):
        bot.send_message(uid, "❌ الرجاء إرسال رابط صالح للفيديو")
        return

# =========================
bot.polling()
