import telebot
from telebot import types
import yt_dlp
import threading
import time
import re
import os
import json
from datetime import datetime

# =========================
# إعدادات البوت
TOKEN = "8600251500:AAH1eo_1QzM4tTNPF2Vb_MxzYgkasMqK6CQ"
CHANNEL = "@VideoExpressA"
TIKTOK_ACCOUNT = "https://www.tiktok.com/@a_max24"
DEVELOPER_ID = 7100818250

bot = telebot.TeleBot(TOKEN)

# =========================
# قاعدة بيانات
DATA_FILE = "users.json"

def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f)

users = load_users()

# =========================
# حماية سبام
last_request = {}

# =========================
# القائمة
def menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 تحميل فيديو", "🎯 تيكتوك")
    markup.add("👥 دعوة صديق")
    if int(uid) == DEVELOPER_ID:
        markup.add("👑 لوحة المطور")
    return markup

# =========================
# إنشاء مستخدم
def check_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            'points': 3,
            'tiktok': False,
            'current_action': None,
            'last_daily': None,
            'downloads': 0,
            'invited_users': []
        }
        save_users()

# =========================
# تحقق الانضمام
def check_join(uid):
    try:
        member = bot.get_chat_member(CHANNEL, int(uid))
        if member.status in ["member", "administrator", "creator"]:
            return True
        else:
            bot.send_message(uid, f"❌ يجب الانضمام إلى القناة:\n{CHANNEL}", reply_markup=menu(uid))
            return False
    except:
        bot.send_message(uid, "❌ تأكد أن البوت مشرف في القناة", reply_markup=menu(uid))
        return False

# =========================
# هدية يومية
def daily_points():
    while True:
        today = datetime.now().strftime("%Y-%m-%d")
        for uid in users:
            if users[uid]['last_daily'] != today:
                users[uid]['points'] += 1
                users[uid]['last_daily'] = today
        save_users()
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
    uid = str(uid)

    if users[uid]['points'] <= 0:
        bot.send_message(uid, "❌ رصيدك صفر!", reply_markup=menu(uid))
        return

    try:
        with open(filename, "rb") as f:
            bot.send_video(uid, f)

        users[uid]['downloads'] += 1
        users[uid]['points'] = max(0, users[uid]['points'] - 1)

        if users[uid]['points'] < 0:
            users[uid]['points'] = 0

        save_users()

        threading.Thread(target=delete_later, args=(filename,)).start()

        bot.send_message(uid, f"✅ تم الإرسال!\n💰 رصيدك: {users[uid]['points']}", reply_markup=menu(uid))

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ: {str(e)}", reply_markup=menu(uid))

# =========================
def download_media(url, uid):
    uid = str(uid)

    if users[uid]['points'] <= 0:
        bot.send_message(uid, "❌ رصيدك صفر!", reply_markup=menu(uid))
        return

    # روابط مدعومة فقط
    if not any(site in url for site in ["youtube", "youtu.be", "tiktok", "instagram"]):
        bot.send_message(uid, "❌ هذا الرابط غير مدعوم", reply_markup=menu(uid))
        return

    bot.send_message(uid, "📥 جاري المعالجة...\n⏳ انتظر قليلاً", reply_markup=menu(uid))

    ydl_opts = {
        'outtmpl': f'{uid}_%(title)s.%(ext)s',
        'noplaylist': True,
        'format': 'bestvideo+bestaudio/best',
        'ffmpeg_location': '/usr/bin/ffmpeg',
        'max_filesize': 50 * 1024 * 1024
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        send_file(uid, filename)

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ: {str(e)}", reply_markup=menu(uid))

# =========================
@bot.message_handler(commands=['start'])
def start(msg):
    uid = str(msg.from_user.id)
    check_user(uid)

    args = msg.text.split()

    if len(args) > 1:
        inviter = args[1]
        if inviter != uid and inviter in users:
            if uid not in users[inviter]['invited_users']:
                users[inviter]['points'] += 3
                users[inviter]['invited_users'].append(uid)
                save_users()
                bot.send_message(inviter, "🎉 دخل شخص عبر رابطك! +3 نقاط")

    bot.send_message(uid, "👋 مرحبًا بك!", reply_markup=menu(uid))

# =========================
@bot.message_handler(func=lambda m: True)
def handle(msg):
    uid = str(msg.from_user.id)
    text = msg.text

    check_user(uid)

    # حماية سبام
    now = time.time()
    if uid in last_request and now - last_request[uid] < 3:
        bot.send_message(uid, "⏳ انتظر قليلاً", reply_markup=menu(uid))
        return
    last_request[uid] = now

    # تحقق الانضمام
    if not check_join(uid):
        return

    if text == "👥 دعوة صديق":
        link = f"https://t.me/{CHANNEL.replace('@','')}?start={uid}"
        bot.send_message(uid, f"🔗 رابطك:\n{link}", reply_markup=menu(uid))
        return

    if text == "🎯 تيكتوك":
        if not users[uid]['tiktok']:
            users[uid]['points'] += 4
            users[uid]['tiktok'] = True
            save_users()
            bot.send_message(uid, f"{TIKTOK_ACCOUNT}\n🎉 +4 نقاط", reply_markup=menu(uid))
        else:
            bot.send_message(uid, "✅ استلمت من قبل", reply_markup=menu(uid))
        return

    if text == "📥 تحميل فيديو":
        users[uid]['current_action'] = "download"
        bot.send_message(uid, "📎 أرسل الرابط", reply_markup=menu(uid))
        return

    if text == "👑 لوحة المطور" and int(uid) == DEVELOPER_ID:
        stats = f"""
👤 المستخدمين: {len(users)}
💰 النقاط: {sum(u['points'] for u in users.values())}
📥 التحميلات: {sum(u['downloads'] for u in users.values())}
"""
        bot.send_message(uid, stats, reply_markup=menu(uid))
        return

    if text and is_url(text):
        if users[uid]['current_action'] != "download":
            bot.send_message(uid, "❌ اختر تحميل فيديو أولاً", reply_markup=menu(uid))
            return

        threading.Thread(target=download_media, args=(text, uid)).start()
        return

    bot.send_message(uid, "⚠️ استخدم الأزرار فقط", reply_markup=menu(uid))

# =========================
bot.polling()
