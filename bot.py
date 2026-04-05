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
TOKEN = "8600251500:AAH1eo_1QzM4tTNPF2Vb_MxzYgkasMqK6CQ"  # توكن البوت
CHANNEL = "@VideoExpressA"  # معرف القناة (بدون رابط كامل)
TIKTOK_ACCOUNT = "https://www.tiktok.com/@a_max24"
DEVELOPER_ID = 7100818250  # معرفك كمالك للبوت

bot = telebot.TeleBot(TOKEN)
users = {}

# =========================
# فحص المستخدم وإعطاء رصيد البداية
def check_user(uid):
    if uid not in users:
        users[uid] = {
            'points': 3,          # رصيد البداية
            'tiktok': False,
            'current_action': None,
            'last_daily': None,
            'downloads': 0,
            'audios': 0
        }

# =========================
# قائمة الأزرار
def menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 تحميل فيديو")  # إزالة خيار استخراج الصوت حسب طلبك
    markup.add("👥 دعوة صديق", "🎯 تيكتوك")
    if uid == DEVELOPER_ID:
        markup.add("👑 لوحة المطور")
    return markup

# زر رجوع
def back_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("↩️ رجوع")
    return markup

# =========================
# فحص الانضمام للقناة
def is_subscribed(uid):
    try:
        member = bot.get_chat_member(CHANNEL, uid)
        return member.status in ['member', 'creator', 'administrator']
    except:
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
                try:
                    bot.send_message(uid, "🎁 تم إضافة نقطة يومية!")
                except:
                    pass
        time.sleep(3600)

threading.Thread(target=daily_points, daemon=True).start()

# =========================
# تحقق من رابط
def is_url(text):
    return re.match(r'^https?://', text)

# =========================
# حذف الملفات بعد فترة
def delete_later(file):
    time.sleep(120)
    if os.path.exists(file):
        os.remove(file)

# =========================
# إرسال الملفات
def send_file(uid, filename):
    try:
        with open(filename, "rb") as f:
            bot.send_video(uid, f)
            users[uid]['downloads'] += 1
        threading.Thread(target=delete_later, args=(filename,)).start()
    except Exception as e:
        bot.send_message(uid, f"❌ خطأ إرسال الملف: {str(e)}")

# =========================
# تحميل من رابط
def download_media(url, uid):
    if users[uid]['points'] <= 0:
        bot.send_message(uid, "❌ انتهى رصيدك، أضف صديقًا أو اضغط على تيكتوك للحصول على نقاط")
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

        users[uid]['points'] -= 1
        bot.send_message(uid, f"✅ تم بنجاح! رصيدك الآن: {users[uid]['points']} نقاط")
        send_file(uid, filename)

    except Exception as e:
        bot.send_message(uid, f"❌ خطأ: {str(e)}")

# =========================
# التعامل مع الرسائل
@bot.message_handler(func=lambda m: True, content_types=['text','document'])
def handle(msg):
    uid = msg.from_user.id
    text = msg.text
    check_user(uid)

    # التحقق من الاشتراك بالقناة
    if not is_subscribed(uid):
        bot.send_message(uid, f"❌ يجب أن تنضم إلى القناة {CHANNEL} أولاً لتستخدم البوت")
        return

    # زر رجوع
    if text == "↩️ رجوع":
        bot.send_message(uid, "🔙 رجوع", reply_markup=menu(uid))
        users[uid]['current_action'] = None
        return

    # دعوة صديق
    if text == "👥 دعوة صديق":
        link = f"https://t.me/{CHANNEL}?start={uid}"
        bot.send_message(uid, f"رابطك:\n{link}\n✅ تم إضافة 3 نقاط عند انضمام صديقك")
        users[uid]['points'] += 3
        return

    # تيكتوك
    if text == "🎯 تيكتوك":
        if not users[uid]['tiktok']:
            bot.send_message(uid, TIKTOK_ACCOUNT)
            users[uid]['points'] += 4
            users[uid]['tiktok'] = True
            bot.send_message(uid, f"✅ تم إضافة 4 نقاط! رصيدك الآن: {users[uid]['points']}")
        return

    # تحميل فيديو
    if text == "📥 تحميل فيديو":
        users[uid]['current_action'] = text
        bot.send_message(uid, "📎 أرسل رابط الفيديو", reply_markup=back_button())
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

        # خيار لإضافة نقاط للجميع
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("↩️ رجوع")
        markup.add("➕ إضافة نقاط للجميع")
        bot.send_message(uid, "اختر العملية:", reply_markup=markup)
        return

    # إضافة نقاط للجميع (خاصية المطور)
    if text == "➕ إضافة نقاط للجميع" and uid == DEVELOPER_ID:
        for u in users:
            users[u]['points'] += 3
        bot.send_message(uid, "✅ تم إضافة 3 نقاط لكل المستخدمين")
        return

    # رابط
    if text and is_url(text):
        action = users[uid]['current_action']
        if not action:
            bot.send_message(uid, "❌ اختر العملية أولاً")
            return

        threading.Thread(target=download_media, args=(text, uid)).start()
        return

    # أي شيء آخر
    if text and not is_url(text):
        bot.send_message(uid, "❌ هذا ليس رابطًا، الرجاء إرسال رابط صالح")
        return

# =========================
bot.polling()
