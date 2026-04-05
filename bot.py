import telebot
from telebot import types
import yt_dlp
import threading
import time
import re
import os
import json
from datetime import datetime, timedelta

# =========================
# إعدادات البوت
TOKEN = "8600251500:AAH1eo_1QzM4tTNPF2Vb_MxzYgkasMqK6CQ"
CHANNEL = "@VideoExpressA"
TIKTOK_ACCOUNT = "https://www.tiktok.com/@a_max24"
DEVELOPER_ID = 7100818250
VIP_DURATION_DAYS = 30  # مدة VIP عند الحصول عليه

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
# حماية سبام محسّنة
last_request = {}

def can_request(uid):
    now = time.time()
    if uid in last_request and now - last_request[uid] < 2:  # تقليل وقت الانتظار
        return False
    last_request[uid] = now
    return True

# =========================
# القائمة
def menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 تحميل فيديو", "🎯 تيكتوك")
    markup.add("👥 دعوة صديق", "🏆 المتصدرون")
    markup.add("💎 VIP")
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
            'invited_users': [],
            'vip_until': None
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
        updated = False
        for uid in users:
            if users[uid]['last_daily'] != today:
                users[uid]['points'] += 1
                users[uid]['last_daily'] = today
                updated = True
        if updated:
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
    if not is_vip(uid) and users[uid]['points'] <= 0:
        bot.send_message(uid, "❌ رصيدك صفر!", reply_markup=menu(uid))
        return
    try:
        with open(filename, "rb") as f:
            bot.send_video(uid, f)

        users[uid]['downloads'] += 1
        if not is_vip(uid):
            users[uid]['points'] = max(0, users[uid]['points'] - 1)
        save_users()

        threading.Thread(target=delete_later, args=(filename,)).start()
        remaining_points = users[uid]['points'] if not is_vip(uid) else "∞"
        bot.send_message(uid, f"✅ تم الإرسال!\n💰 رصيدك: {remaining_points}", reply_markup=menu(uid))
    except Exception as e:
        bot.send_message(uid, f"❌ خطأ: {str(e)}", reply_markup=menu(uid))

# =========================
def download_media(url, uid):
    uid = str(uid)
    if not is_vip(uid) and users[uid]['points'] <= 0:
        bot.send_message(uid, "❌ رصيدك صفر!", reply_markup=menu(uid))
        return
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

    def worker():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            send_file(uid, filename)
        except Exception as e:
            bot.send_message(uid, f"❌ خطأ: {str(e)}", reply_markup=menu(uid))

    threading.Thread(target=worker).start()  # تنزيل في خيط مستقل

# =========================
def is_vip(uid):
    uid = str(uid)
    vip_until = users[uid].get('vip_until')
    if vip_until:
        vip_time = datetime.fromisoformat(vip_until)
        if vip_time > datetime.now():
            return True
        else:
            users[uid]['vip_until'] = None
            save_users()
    return False

# =========================
def dev_stats():
    total_users = len(users)
    total_points = sum(u['points'] for u in users.values())
    total_downloads = sum(u['downloads'] for u in users.values())
    total_vip = sum(1 for u in users.values() if is_vip(u))
    return f"""👤 المستخدمين: {total_users}
💰 مجموع النقاط: {total_points}
📥 مجموع التحميلات: {total_downloads}
💎 VIP نشط: {total_vip}"""

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
                users[inviter]['invited_users'].append(uid)
                # مكافآت الإحالات
                if len(users[inviter]['invited_users']) == 5:
                    users[inviter]['points'] += 10
                    bot.send_message(inviter, "🎉 لقد وصلت 5 دعوات! +10 نقاط")
                elif len(users[inviter]['invited_users']) == 15:
                    users[inviter]['vip_until'] = (datetime.now() + timedelta(days=VIP_DURATION_DAYS)).isoformat()
                    bot.send_message(inviter, f"💎 تهانينا! VIP لمدة {VIP_DURATION_DAYS} يوم")
                save_users()

    bot.send_message(uid, "👋 مرحبًا بك!", reply_markup=menu(uid))

# =========================
@bot.message_handler(func=lambda m: True)
def handle(msg):
    uid = str(msg.from_user.id)
    text = msg.text
    check_user(uid)

    if not can_request(uid):
        bot.send_message(uid, "⏳ انتظر قليلاً", reply_markup=menu(uid))
        return

    if not check_join(uid):
        return

    if text == "👥 دعوة صديق":
        link = f"https://t.me/{CHANNEL.replace('@','')}?start={uid}"
        bot.send_message(uid, f"🔗 رابطك:\n{link}\n🎯 شاركه للحصول على نقاط إضافية!", reply_markup=menu(uid))
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

    if text == "💎 VIP":
        vip_status = "نشط" if is_vip(uid) else "غير نشط"
        features = "🎬 تحميل غير محدود\n⚡ سرعة عالية\n💡 كلمات تحفيزية: مرحبا يازعيم" if is_vip(uid) else "💡 VIP متاح فقط عند دعوة 15 شخص"
        bot.send_message(uid, f"💎 VIP: {vip_status}\n{features}", reply_markup=menu(uid))
        return

    if text == "🏆 المتصدرون":
        sorted_users = sorted(users.items(), key=lambda x: (x[1]['points'], x[1]['downloads']), reverse=True)
        leaderboard = "🏆 المتصدرون:\n\n"
        for i, (u, data) in enumerate(sorted_users[:10], start=1):
            vip_mark = "💎" if is_vip(u) else ""
            leaderboard += f"{i}. {u} {vip_mark} - نقاط: {data['points']}, تحميلات: {data['downloads']}\n"
        bot.send_message(uid, leaderboard, reply_markup=menu(uid))
        return

    if text == "👑 لوحة المطور" and int(uid) == DEVELOPER_ID:
        bot.send_message(uid, dev_stats(), reply_markup=menu(uid))
        return

    if text and is_url(text):
        if users[uid]['current_action'] != "download":
            bot.send_message(uid, "❌ اختر تحميل فيديو أولاً", reply_markup=menu(uid))
            return
        download_media(text, uid)
        return

    bot.send_message(uid, "⚠️ استخدم الأزرار فقط", reply_markup=menu(uid))

# =========================
bot.polling()
