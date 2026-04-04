import telebot
from telebot import types
import yt_dlp
import threading
import time
import re
import os

# =========================
# إعدادات البوت
TOKEN = "8600251500:AAH1eo_1QzM4tTNPF2Vb_MxzYgkasMqK6CQ"
CHANNEL = "https://t.me/VideoExpressA"
TIKTOK_ACCOUNT = "https://www.tiktok.com/@a_max24"
DEVELOPER_ID = 7100818250  # رقمك الخاص على تيليغرام
bot = telebot.TeleBot(TOKEN)

# =========================
# قاعدة بيانات المستخدمين
users = {}  
# {user_id: {'points': int, 'invited': int, 'tiktok': False, 'current_action': None,
#            'last_daily': str, 'downloads': int, 'audios': int}}

# =========================
# قائمة رئيسية
def menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 تحميل فيديو", "🎵 استخراج صوت")
    markup.add("👥 دعوة صديق", "🎯 تيكتوك")
    if uid == DEVELOPER_ID:
        markup.add("👑 لوحة المطور")
    return markup

# =========================
# التحقق من المستخدم
def check_user(uid):
    if uid not in users:
        users[uid] = {'points': 5, 'invited': 0, 'tiktok': False, 'current_action': None,
                      'last_daily': None, 'downloads': 0, 'audios': 0}

# =========================
# إضافة نقاط تيكتوك بعد 7 ثوانٍ
def add_tiktok_points(uid):
    time.sleep(7)
    users[uid]['points'] += 4
    users[uid]['tiktok'] = True
    bot.send_message(uid, f"✅ تمت إضافة 4 نقاط لاشتراكك في تيكتوك!\n🔹 نقاطك: {users[uid]['points']}")

# =========================
# التحقق إذا النص رابط
def is_url(text):
    return re.match(r'^https?://', text)

# =========================
# إرسال الملف بعد التحميل
def send_file(uid, filename, action_type):
    try:
        with open(filename, "rb") as f:
            if filename.endswith(".mp3"):
                bot.send_audio(uid, f)
                users[uid]['audios'] += 1
            else:
                bot.send_video(uid, f)
                users[uid]['downloads'] += 1
        os.remove(filename)
    except Exception as e:
        bot.send_message(uid, f"❌ لم أتمكن من إرسال الملف: {str(e)}")

# =========================
# Daily Bonus
def daily_bonus():
    while True:
        now_day = time.strftime("%Y-%m-%d")
        for uid in users:
            if 'last_daily' not in users[uid] or users[uid]['last_daily'] != now_day:
                users[uid]['points'] += 1
                users[uid]['last_daily'] = now_day
                try:
                    bot.send_message(uid, f"🎁 تم إضافة نقطة يومية!\nنقاطك الآن: {users[uid]['points']}")
                except:
                    pass
        time.sleep(3600)

# =========================
# استقبال الرسائل
@bot.message_handler(func=lambda m: True, content_types=['text','document'])
def handle(msg):
    uid = msg.from_user.id
    text = msg.text
    check_user(uid)

    # زر رجوع
    if text == "↩️ رجوع":
        bot.send_message(uid, "🔙 رجعت للقائمة الرئيسية", reply_markup=menu(uid))
        users[uid]['current_action'] = None
        return

    # دعوة صديق
    if text == "👥 دعوة صديق":
        link = f"{CHANNEL}?start={uid}"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("↩️ رجوع")
        bot.send_message(uid, f"رابط دعوتك:\n{link}\n🔹 نقاطك: {users[uid]['points']}", reply_markup=markup)
        return

    # تيكتوك
    if text == "🎯 تيكتوك":
        if not users[uid]['tiktok']:
            bot.send_message(uid, f"🔗 هذا رابط تيكتوك الخاص بك: {TIKTOK_ACCOUNT}")
            threading.Thread(target=add_tiktok_points, args=(uid,)).start()
        else:
            bot.send_message(uid, "لقد استخدمت هذا الخيار من قبل!")
        return

    # اختيار العملية
    if text in ["📥 تحميل فيديو", "🎵 استخراج صوت"]:
        users[uid]['current_action'] = text
        bot.send_message(uid, "أرسل رابط الفيديو الآن أو أرسل ملف الفيديو:", reply_markup=types.ReplyKeyboardMarkup().add("↩️ رجوع"))
        return

    # روابط فيديو
    if text and is_url(text):
        action = users[uid]['current_action']
        if not action:
            bot.send_message(uid, "❌ الرجاء اختيار العملية أولاً.", reply_markup=menu(uid))
            return

        ydl_opts = {}
        if action == "📥 تحميل فيديو":
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': f'{uid}_%(title)s.%(ext)s',
                'noplaylist': True,
            }
        elif action == "🎵 استخراج صوت":
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{uid}_%(title)s.%(ext)s',
                'noplaylist': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=True)
                filename = ydl.prepare_filename(info)
                if action == "🎵 استخراج صوت":
                    filename = filename.rsplit('.', 1)[0] + ".mp3"

            users[uid]['points'] -= 1
            bot.send_message(uid, f"✅ تمت العملية بنجاح!\n🔹 نقاطك الحالية: {users[uid]['points']}\n📁 جاري إرسال الملف...")
            threading.Thread(target=send_file, args=(uid, filename, action)).start()

        except Exception as e:
            bot.send_message(uid, f"❌ خطأ في التحميل: {str(e)}\n🔹 تأكد أن الرابط صالح ويدعم التحميل.")
        users[uid]['current_action'] = None
        return

    # لوحة المطور
    if text == "👑 لوحة المطور" and uid == DEVELOPER_ID:
        stats = "📊 إحصائيات المستخدمين اليومية:\n\n"
        for u_id, data in users.items():
            stats += f"👤 {u_id}\nنقاط: {data['points']}\nتحميل فيديو: {data['downloads']}\nاستخراج صوت: {data['audios']}\n\n"
        bot.send_message(uid, stats)
        return

    # أي نص غير معروف
    bot.send_message(uid, "❌ أمر غير صالح. الرجاء استخدام الأزرار فقط.", reply_markup=menu(uid))

# =========================
# بدء البوت وتشغيل Daily Bonus
threading.Thread(target=daily_bonus, daemon=True).start()
bot.polling()
