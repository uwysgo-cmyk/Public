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
users = {}  # {user_id: {'points': int, 'invited': int, 'tiktok': False, 'current_action': None, 'daily_claimed': False}}

# =========================
# قائمة رئيسية
def menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 تحميل فيديو", "🎵 استخراج صوت")
    markup.add("👥 دعوة صديق", "🎯 تيكتوك")
    if uid == DEVELOPER_ID:  # لوحة المطور تظهر فقط لك
        markup.add("👑 لوحة المطور")
    return markup

# =========================
# التحقق من المستخدم
def check_user(uid):
    if uid not in users:
        users[uid] = {'points': 5, 'invited': 0, 'tiktok': False, 'current_action': None, 'daily_claimed': False}

# =========================
# إعطاء نقطة يومية
def daily_points():
    while True:
        for uid in users:
            if not users[uid]['daily_claimed']:
                users[uid]['points'] += 1
                try:
                    bot.send_message(uid, "🔹 تم إضافة نقطة يومية لمستخدمك!")
                except:
                    pass
                users[uid]['daily_claimed'] = True
        # إعادة ضبط كل يوم (86400 ثانية)
        time.sleep(86400)
        for uid in users:
            users[uid]['daily_claimed'] = False

# =========================
# إضافة نقاط تيكتوك
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
def send_file(uid, filename):
    try:
        with open(filename, "rb") as f:
            if filename.endswith(".mp3"):
                bot.send_audio(uid, f)
            else:
                bot.send_video(uid, f)
        os.remove(filename)  # حذف الملف بعد الإرسال
    except Exception as e:
        bot.send_message(uid, f"❌ لم أتمكن من إرسال الملف: {str(e)}")

# =========================
# خيارات yt-dlp
def download_media(url, uid, action):
    ydl_opts = {}
    ffmpeg_path = '/usr/bin/ffmpeg'  # تأكد أنه موجود على السيرفر

    if action == "📥 تحميل فيديو":
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': f'{uid}_%(title)s.%(ext)s',
            'noplaylist': True,
            'ffmpeg_location': ffmpeg_path
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
            'ffmpeg_location': ffmpeg_path
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if action == "🎵 استخراج صوت":
                filename = filename.rsplit('.', 1)[0] + ".mp3"

        users[uid]['points'] -= 1
        bot.send_message(uid, f"✅ تمت العملية بنجاح!\n🔹 نقاطك الحالية: {users[uid]['points']}\n📁 جاري إرسال الملف...")
        threading.Thread(target=send_file, args=(uid, filename)).start()
    except Exception as e:
        bot.send_message(uid, f"❌ خطأ في التحميل: {str(e)}\n🔹 تأكد أن الرابط صالح ويدعم التحميل.")

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

    # إذا النص رابط فيديو
    if text and is_url(text):
        action = users[uid]['current_action']
        if not action:
            bot.send_message(uid, "❌ الرجاء اختيار العملية أولاً.", reply_markup=menu(uid))
            return
        threading.Thread(target=download_media, args=(text, uid, action)).start()
        users[uid]['current_action'] = None
        return

    # استقبال فيديو من الجهاز
    if msg.content_type == 'document':
        file_info = bot.get_file(msg.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        filename = f"{uid}_{msg.document.file_name}"
        with open(filename, 'wb') as f:
            f.write(downloaded_file)
        action = users[uid]['current_action']
        if action == "🎵 استخراج صوت":
            # تحويل الملف المرفوع إلى mp3 باستخدام ffmpeg
            output_mp3 = filename.rsplit('.',1)[0]+".mp3"
            os.system(f"ffmpeg -i {filename} -vn -ar 44100 -ac 2 -b:a 192k {output_mp3}")
            bot.send_message(uid, f"✅ تم استخراج الصوت من الفيديو.")
            threading.Thread(target=send_file, args=(uid, output_mp3)).start()
        users[uid]['current_action'] = None
        return

    # أي نص غير معروف
    bot.send_message(uid, "❌ أمر غير صالح. الرجاء استخدام الأزرار فقط.", reply_markup=menu(uid))

# =========================
# بدء البوت
threading.Thread(target=daily_points, daemon=True).start()  # بدء إضافة نقطة يومية
bot.polling()
