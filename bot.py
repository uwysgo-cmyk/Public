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
CHANNEL = "@VideoExpressA"  # معرف القناة بدون https
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
# التحقق من اشتراك المستخدم بالقناة
def is_subscribed(uid):
    try:
        member = bot.get_chat_member(chat_id=CHANNEL, user_id=uid)
        if member.status in ["member", "creator", "administrator"]:
            return True
        return False
    except:
        return False

# =========================
# هدية يومية (يمكن تعديل لاحقًا)
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
    try:
        if users[uid]['points'] <= 0:
            bot.send_message(uid, "❌ رصيدك انتهى، لا يمكن إتمام العملية.")
            return

        with open(filename, "rb") as f:
            bot.send_video(uid, f)
            users[uid]['downloads'] += 1

        threading.Thread(target=delete_later, args=(filename,)).start()
        users[uid]['points'] -= 1
        bot.send_message(uid, f"✅ تم بنجاح! رصيدك الآن: {users[uid]['points']} نقطة")

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ إرسال الملف: {str(e)}")

# =========================
def download_media(url, uid):
    if users[uid]['points'] <= 0:
        bot.send_message(uid, "❌ رصيدك انتهى، لا يمكن إتمام العملية.")
        return

    if not is_subscribed(uid):
        bot.send_message(uid, f"❌ يجب عليك الانضمام إلى القناة أولاً: {CHANNEL}")
        return

    bot.send_message(uid, "⏳ جاري التحميل...")

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

    # الدعوة
    if text == "👥 دعوة صديق":
        link = f"https://t.me/VideoExpressA?start={uid}"
        bot.send_message(uid, f"رابطك:\n{link}")
        users[uid]['points'] += 3
        bot.send_message(uid, f"🎉 تم إضافة 3 نقاط لرصيدك! رصيدك الآن: {users[uid]['points']} نقطة")
        return

    # تيكتوك
    if text == "🎯 تيكتوك":
        if users[uid]['points'] <= 0:
            bot.send_message(uid, "❌ رصيدك انتهى، لا يمكن إتمام العملية.")
            return

        if not is_subscribed(uid):
            bot.send_message(uid, f"❌ يجب عليك الانضمام إلى القناة أولاً: {CHANNEL}")
            return

        if not users[uid]['tiktok']:
            bot.send_message(uid, TIKTOK_ACCOUNT)
            users[uid]['points'] += 4
            users[uid]['tiktok'] = True
            bot.send_message(uid, f"🎉 تم إضافة 4 نقاط لرصيدك! رصيدك الآن: {users[uid]['points']} نقطة")
        return

    # تحميل فيديو
    if is_url(text):
        download_media(text, uid)
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
        bot.send_message(uid, msg_stats)

        # إضافة نقاط لجميع المستخدمين (ميزة مطور)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ إضافة نقاط للجميع")
        sent = bot.send_message(uid, "يمكنك إضافة نقاط لجميع المستخدمين:", reply_markup=markup)
        return

bot.polling()
