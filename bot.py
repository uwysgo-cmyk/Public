import telebot
from telebot import types
import yt_dlp
import threading
import time
import re
import os
from datetime import datetime

# =========================
# إعدادات البوت
TOKEN = os.getenv("TOKEN")  # ضع توكن البوت كمتغير بيئة
CHANNEL = "https://t.me/VideoExpressA"
TIKTOK_ACCOUNT = "https://www.tiktok.com/@a_max24"
DEVELOPER_ID = 7100818250  # رقمك على تيليغرام

bot = telebot.TeleBot(TOKEN)
users = {}

# =========================
# قائمة أزرار دائمة
def menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 تحميل فيديو", "🎯 تيكتوك")
    markup.add("👥 دعوة صديق")
    if uid == DEVELOPER_ID:
        markup.add("👑 لوحة المطور")
    markup.add("↩️ رجوع")
    return markup

# =========================
# التحقق من المستخدم
def check_user(uid):
    if uid not in users:
        users[uid] = {
            'points': 3,
            'tiktok': False,
            'current_action': None,
            'last_daily': None,
            'downloads': 0
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
                    bot.send_message(uid, f"🎁 تم إضافة نقطة يومية! رصيدك الحالي: {users[uid]['points']}", reply_markup=menu(uid))
                except:
                    pass
        time.sleep(3600)

threading.Thread(target=daily_points, daemon=True).start()

# =========================
# التحقق من رابط
def is_url(text):
    return re.match(r'^https?://', text)

# =========================
# حذف الملفات بعد فترة
def delete_later(file):
    time.sleep(120)
    if os.path.exists(file):
        os.remove(file)

# =========================
# إرسال الفيديو
def send_file(uid, filename):
    try:
        with open(filename, "rb") as f:
            bot.send_video(uid, f)
            users[uid]['downloads'] += 1
            users[uid]['points'] -= 1
        threading.Thread(target=delete_later, args=(filename,)).start()
        bot.send_message(uid, f"✅ تم الإرسال بنجاح! رصيدك الحالي: {users[uid]['points']}", reply_markup=menu(uid))
    except Exception as e:
        bot.send_message(uid, f"❌ خطأ إرسال الملف: {str(e)}", reply_markup=menu(uid))

# =========================
# تنزيل الفيديو
def download_media(url, uid):
    if users[uid]['points'] <= 0:
        bot.send_message(uid, "❌ رصيدك صفر! شارك القناة أو انتظر النقاط اليومية.", reply_markup=menu(uid))
        return

    bot.send_message(uid, "⏳ جاري تحميل الفيديو...", reply_markup=menu(uid))
    ydl_opts = {
        'outtmpl': f'{uid}_%(title)s.%(ext)s',
        'noplaylist': True,
        'format': 'bestvideo+bestaudio/best',
        'ffmpeg_location': '/usr/bin/ffmpeg'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        send_file(uid, filename)
    except Exception as e:
        bot.send_message(uid, f"❌ خطأ: {str(e)}\n🔹 تأكد أن الرابط صالح ويدعم التحميل.", reply_markup=menu(uid))

# =========================
# التعامل مع الرسائل
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle(msg):
    uid = msg.from_user.id
    text = msg.text
    check_user(uid)

    # التحقق من الاشتراك في القناة
    try:
        member = bot.get_chat_member(CHANNEL, uid)
        if member.status in ['left', 'kicked']:
            bot.send_message(uid, f"❌ يجب الانضمام إلى القناة أولاً: {CHANNEL}", reply_markup=menu(uid))
            return
    except:
        bot.send_message(uid, f"❌ لم أتمكن من التحقق من الاشتراك. تأكد من أن البوت مشرف في القناة.", reply_markup=menu(uid))
        return

    # إشعار إذا كانت النقاط صفر
    if users[uid]['points'] <= 0:
        bot.send_message(uid, "⚠️ رصيدك صفر! شارك القناة أو انتظر النقاط اليومية.", reply_markup=menu(uid))

    # زر الرجوع
    if text == "↩️ رجوع":
        users[uid]['current_action'] = None
        bot.send_message(uid, "🔙 رجوع", reply_markup=menu(uid))
        return

    # دعوة صديق
    if text == "👥 دعوة صديق":
        users[uid]['points'] += 3
        link = f"{CHANNEL}?start={uid}"
        bot.send_message(uid, f"رابطك:\n{link}\n🎉 تم إضافة 3 نقاط! رصيدك: {users[uid]['points']}", reply_markup=menu(uid))
        return

    # تيكتوك
    if text == "🎯 تيكتوك":
        if not users[uid]['tiktok']:
            users[uid]['points'] += 4
            users[uid]['tiktok'] = True
            bot.send_message(uid, f"{TIKTOK_ACCOUNT}\n🎉 تم إضافة 4 نقاط! رصيدك: {users[uid]['points']}", reply_markup=menu(uid))
        else:
            bot.send_message(uid, "✅ لقد استلمت رابط تيكتوك مسبقًا.", reply_markup=menu(uid))
        return

    # تحميل فيديو
    if text == "📥 تحميل فيديو":
        if users[uid]['points'] <= 0:
            bot.send_message(uid, "⚠️ رصيدك صفر! لا يمكنك تحميل فيديو.", reply_markup=menu(uid))
            return
        users[uid]['current_action'] = "download"
        bot.send_message(uid, "أرسل رابط الفيديو للتحميل", reply_markup=menu(uid))
        return

    # لوحة المطور
    if text == "👑 لوحة المطور" and uid == DEVELOPER_ID:
        total_users = len(users)
        total_points = sum(u['points'] for u in users.values())
        total_downloads = sum(u['downloads'] for u in users.values())
        msg_stats = f"""
📊 إحصائيات:
👤 المستخدمين: {total_users}
💰 مجموع النقاط: {total_points}
🎬 تحميل فيديو: {total_downloads}
"""
        bot.send_message(uid, msg_stats, reply_markup=menu(uid))
        return

    # التحقق من الرابط
    if text and is_url(text):
        action = users[uid]['current_action']
        if action != "download":
            bot.send_message(uid, "❌ اختر العملية أولاً (تحميل فيديو)", reply_markup=menu(uid))
            return
        threading.Thread(target=download_media, args=(text, uid)).start()
        return

    # إدخال غير صالح
    bot.send_message(uid, "⚠️ هذا ليس رابطًا صالحًا أو أمرًا معروفًا.", reply_markup=menu(uid))

# =========================
bot.polling()
