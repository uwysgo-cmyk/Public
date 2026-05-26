import telebot
from telebot import types
import yt_dlp
import threading
import time
import os
import json
from datetime import datetime

# ==========================================
# إعدادات البوت الأساسية والروابط الخاصة بك
# ==========================================
TOKEN = "8600251500:AAH1eo_1QzM4tTNPF2Vb_MxzYgkasMqK6CQ"
CHANNEL = "@VideoExpressA"
TIKTOK_ACCOUNT = "https://www.tiktok.com/@a_max24"
DEVELOPER_ID = 7100818250

bot = telebot.TeleBot(TOKEN)
db_lock = threading.Lock()

# ==========================================
# إدارة قاعدة البيانات والملفات
# ==========================================
DATA_FILE = "users.json"
CONFIG_FILE = "config.json"

def load_users():
    with db_lock:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

def save_users():
    with db_lock:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=4)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"bot_active": True}

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

users = load_users()
config = load_config()
last_request = {}

# ==========================================
# الحماية ونظام التحقق من الاشتراك الإجباري
# ==========================================
def can_request(uid):
    now = time.time()
    if uid in last_request and now - last_request[uid] < 2:
        return False
    last_request[uid] = now
    return True

def check_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            'points': 5,            # هدية الدخول لأول مرة
            'tiktok': False,
            'last_daily': None,
            'downloads': 0
        }
        save_users()

def check_join(uid):
    if int(uid) == DEVELOPER_ID:
        return True
    try:
        member = bot.get_chat_member(CHANNEL, int(uid))
        if member.status in ["member", "administrator", "creator"]:
            return True
        else:
            bot.send_message(uid, f"❌ تم إيقاف البوت! يجب الانضمام إلى قناتنا أولاً لتتمكن من استخدامه:\n{CHANNEL}")
            return False
    except:
        bot.send_message(uid, "❌ تأكد من أن البوت مشرف في القناة الخاصة بك لتفعيل الفحص التلقائي.")
        return False

# ==========================================
# لوحات التحكم والأزرار الرئيسية
# ==========================================
def menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 تحميل فيديو", "🎯 تيكتوك")
    markup.add("💡 حول البوت")
    if int(uid) == DEVELOPER_ID:
        markup.add("👑 لوحة المطور")
    return markup

# ==========================================
# الهدية التلقائية (نقطة واحدة كل يومين)
# ==========================================
def daily_points_checker():
    while True:
        try:
            now = datetime.now()
            updated = False
            for uid in list(users.keys()):
                last_daily_str = users[uid].get('last_daily')
                if last_daily_str:
                    last_daily_time = datetime.fromisoformat(last_daily_str)
                    if (now - last_daily_time).total_seconds() >= 172800: # 48 ساعة كاملة
                        users[uid]['points'] += 1
                        users[uid]['last_daily'] = now.isoformat()
                        updated = True
                else:
                    users[uid]['last_daily'] = now.isoformat()
                    updated = True
            if updated:
                save_users()
        except:
            pass
        time.sleep(3600)

threading.Thread(target=daily_points_checker, daemon=True).start()

# ==========================================
# معالجة الوسائط (التحميل التلقائي ونزع الصوت)
# ==========================================
def delete_later(file_path):
    time.sleep(120)
    if os.path.exists(file_path):
        try: os.remove(file_path)
        except: pass

def download_media(url, uid):
    uid = str(uid)
    if users[uid]['points'] <= 0:
        bot.send_message(uid, "❌ رصيدك صفر! يرجى كسب نقاط لتتمكن من التحميل.", reply_markup=menu(uid))
        return

    msg = bot.send_message(uid, "📥 جاري معالجة الرابط والتحميل تلقائياً... ⏳", reply_markup=menu(uid))
    
    import static_ffmpeg
    static_ffmpeg.add_paths()

    ydl_opts = {
        'outtmpl': f'downloads/{uid}_%(title)s.%(ext)s',
        'noplaylist': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'max_filesize': 45 * 1024 * 1024
    }

    try:
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
        with open(filename, "rb") as f:
            bot.send_video(uid, f, caption="✅ تم التحميل بنجاح عبر البوت!")
            
        users[uid]['downloads'] += 1
        users[uid]['points'] = max(0, users[uid]['points'] - 1)
        save_users()
        
        bot.delete_message(uid, msg.message_id)
        bot.send_message(uid, f"💰 تم خصم نقطة واحدة. رصيدك المتبقي: {users[uid]['points']}", reply_markup=menu(uid))
        threading.Thread(target=delete_later, args=(filename,)).start()
    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ أثناء التحميل: {str(e)}", uid, msg.message_id)

def extract_audio_processing(file_id, file_name, uid):
    uid = str(uid)
    msg = bot.send_message(uid, "🎵 جاري نزع الصوت من المقطع وتحويله إلى MP3... ⏳")
    
    import static_ffmpeg
    static_ffmpeg.add_paths()
    import subprocess

    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        input_path = f"downloads/in_{uid}_{file_name}"
        output_path = f"downloads/out_{uid}_{os.path.splitext(file_name)[0]}.mp3"
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
            
        with open(input_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        command = f"ffmpeg -y -i \"{input_path}\" -vn -acodec libmp3lame \"{output_path}\""
        subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(output_path):
            with open(output_path, "rb") as audio:
                bot.send_audio(uid, audio, caption="🎵 تم نزع الصوت بنجاح!")
            users[uid]['points'] = max(0, users[uid]['points'] - 1)
            save_users()
            bot.send_message(uid, f"💰 تم خصم نقطة واحدة. رصيدك الحالي: {users[uid]['points']}")
        else:
            bot.send_message(uid, "❌ فشل استخراج الصوت من الملف.")
            
        bot.delete_message(uid, msg.message_id)
        threading.Thread(target=delete_later, args=(input_path,)).start()
        threading.Thread(target=delete_later, args=(output_path,)).start()
    except Exception as e:
        bot.send_message(uid, f"❌ حدث خطأ: {str(e)}")

# ==========================================
# استقبال الأحداث والأوامر النصية
# ==========================================
@bot.message_handler(commands=['start'])
def start(msg):
    uid = str(msg.from_user.id)
    check_user(uid)
    if not check_join(uid): return
    bot.send_message(uid, "👋 مرحباً بك في بوت تحميل الميديا ونزع الأصوات الاحترافي!", reply_markup=menu(uid))

@bot.message_handler(content_types=['video'])
def handle_incoming_video(msg):
    uid = str(msg.from_user.id)
    check_user(uid)
    if not config["bot_active"] and int(uid) != DEVELOPER_ID:
        bot.send_message(uid, "⚠️ البوت في وضع صيانة مؤقتة حالياً، يرجى العودة لاحقاً.")
        return
    if not check_join(uid): return
    
    if users[uid]['points'] <= 0:
        bot.send_message(uid, "❌ رصيدك 0 نقاط، لا يمكنك تنفيذ هذه العملية.")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎵 نزع الصوت فقط", callback_data=f"extract_{msg.video.file_id}_{uid}"))
    bot.send_message(uid, "🎬 استلمت مقطع الفيديو الخاص بك. اختر الإجراء المطلوب:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("extract_"))
def callback_extract(call):
    _, file_id, uid = call.data.split("_")
    if str(call.from_user.id) != uid:
        bot.answer_callback_query(call.id, "❌ هذا الأمر ليس لك!")
        return
    bot.delete_message(uid, call.message.message_id)
    threading.Thread(target=extract_audio_processing, args=(file_id, "video.mp4", uid)).start()

@bot.message_handler(func=lambda m: True)
def handle(msg):
    uid = str(msg.from_user.id)
    text = msg.text
    check_user(uid)

    if not config["bot_active"] and int(uid) != DEVELOPER_ID:
        bot.send_message(uid, "⚠️ البوت متوقف حالياً للصيانة.")
        return

    if not can_request(uid):
        bot.send_message(uid, "⏳ يرجى الانتظار قليلاً بين الأوامر لمنع الحظر.")
        return

    if not check_join(uid): return

    if text == "💡 حول البوت":
        about_text = (
            "💡 **كيف يعمل البوت؟**\n"
            "1️⃣ أرسل رابط فيديو مباشرة (تيك توك، إنستغرام، يوتيوب) وسيتم تحميله تلقائياً.\n"
            "2️⃣ أرسل ملف فيديو مخزن على هاتفك لتتمكن من نزع الصوت منه وتحويله إلى MP3.\n\n"
            "💰 **كيف تكسب نقاط؟**\n"
            "• تحصل على 5 نقاط عند دخولك البوت لأول مرة.\n"
            "• تمنح نقطة واحدة مجانية تلقائياً كل يومين.\n"
            "• اضغط على زر (🎯 تيكتوك) للحصول على 4 نقاط مجانية إضافية!"
        )
        bot.send_message(uid, about_text, parse_mode="Markdown", reply_markup=menu(uid))
        return

    if text == "🎯 تيكتوك":
        if not users[uid].get('tiktok', False):
            bot.send_message(uid, f"🎯 قم بزيارة حسابنا ومتابعتنا على التيك توك عبر الرابط التالي:\n{TIKTOK_ACCOUNT}\n\n⏳ انتظر 7 ثوانٍ ليتم التحقق وإضافة النقاط...")
            
            def gift_points():
                time.sleep(7)
                users[uid]['points'] += 4
                users[uid]['tiktok'] = True
                save_users()
                bot.send_message(uid, "🎉 تهانينا! مرت 7 ثوانٍ وتم منحك 4 نقاط مكافأة بنجاح طوال فترة استخدامك!", reply_markup=menu(uid))
            
            threading.Thread(target=gift_points).start()
        else:
            bot.send_message(uid, "❌ لقد استلمت الهدية المخصصة للتيك توك مسبقاً، لا يمكن الحصول عليها مجدداً.", reply_markup=menu(uid))
        return

    if text == "📥 تحميل فيديو":
        bot.send_message(uid, "📎 أرسل رابط الفيديو الآن (تيك توك، يوتيوب، إنستغرام):", reply_markup=menu(uid))
        return

    # 👑 لوحة تحكم المطور
    if text == "👑 لوحة المطور" and int(uid) == DEVELOPER_ID:
        dev_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        dev_markup.add("📊 الإحصائيات اليومية", "🔄 تشغيل/إيقاف البوت")
        dev_markup.add("➕ إضافة نقاط للمجموع", "➕ إضافة نقاط لشخص")
        dev_markup.add("➖ خصم نقاط من الجميع", "🔙 العودة للقائمة")
        bot.send_message(uid, "👑 مرحباً بك يا مطور في لوحة التحكم الخاصة بك:", reply_markup=dev_markup)
        return

    if text == "🔙 العودة للقائمة":
        bot.send_message(uid, "🔙 تم العودة للقائمة الرئيسية.", reply_markup=menu(uid))
        return

    if int(uid) == DEVELOPER_ID:
        if text == "📊 الإحصائيات اليومية":
            total_users = len(users)
            total_pts = sum(u.get('points', 0) for u in users.values())
            total_dl = sum(u.get('downloads', 0) for u in users.values())
            status = "🟢 يعمل" if config["bot_active"] else "🔴 متوقف"
            report = f"📊 **إحصائيات البوت الحالية:**\n\n👥 إجمالي المستخدمين: {total_users}\n💰 إجمالي النقاط الموزعة: {total_pts}\n📥 إجمالي التحميلات الناجحة: {total_dl}\n⚙️ حالة البوت الحالية: {status}"
            bot.send_message(uid, report, parse_mode="Markdown")
            return
        
        elif text == "🔄 تشغيل/إيقاف البوت":
            config["bot_active"] = not config["bot_active"]
            save_config()
            state = "🟢 تشغيله" if config["bot_active"] else "🔴 إيقافه"
            bot.send_message(uid, f"⚙️ تم تغيير حالة البوت! تم {state} بنجاح لجميع المستخدمين.")
            return

        elif text == "➕ إضافة نقاط للمجموع":
            msg_step = bot.send_message(uid, "✍️ اكتب عدد النقاط التي تريد إضافتها **لكل** المستخدمين:")
            bot.register_next_step_handler(msg_step, process_add_all)
            return

        elif text == "➕ إضافة نقاط لشخص":
            msg_step = bot.send_message(uid, "✍️ أرسل الـ ID الخاص بالشخص ثم مسافة ثم عدد النقاط (مثال: `7100818250 10`):")
            bot.register_next_step_handler(msg_step, process_add_one)
            return

        elif text == "➖ خصم نقاط من الجميع":
            msg_step = bot.send_message(uid, "✍️ اكتب عدد النقاط التي تريد خصمها من **جميع** المستخدمين:")
            bot.register_next_step_handler(msg_step, process_sub_all)
            return

    # التحميل التلقائي الفوري بمجرد استقبال الرابط المدعوم
    if text.startswith("http://") or text.startswith("https://"):
        if any(site in text for site in ["youtube.com", "youtu.be", "tiktok.com", "instagram.com"]):
            download_media(text, uid)
        else:
            bot.send_message(uid, "❌ عذراً، هذا الرابط من موقع غير مدعوم حالياً.")
        return

    bot.send_message(uid, "⚠️ يرجى استخدام أزرار التحكم الموضحة أسفل الشاشة أو إرسال رابط مدعوم.")

# ==========================================
# معالجة المدخلات المتقدمة للمطور
# ==========================================
def process_add_all(message):
    try:
        pts = int(message.text)
        for u in users: users[u]['points'] += pts
        save_users()
        bot.send_message(DEVELOPER_ID, f"✅ بنجاح، تم إضافة {pts} نقطة لجميع المشتركين.")
    except: bot.send_message(DEVELOPER_ID, "❌ أرسل قيمة رقمية صحيحة فقط.")

def process_add_one(message):
    try:
        target_id, pts = message.text.split()
        pts = int(pts)
        if target_id in users:
            users[target_id]['points'] += pts
            save_users()
            bot.send_message(DEVELOPER_ID, f"✅ تم إضافة {pts} نقطة للحساب {target_id} بنجاح.")
        else: bot.send_message(DEVELOPER_ID, "❌ هذا الحساب غير مسجل في البوت بعد.")
    except: bot.send_message(DEVELOPER_ID, "❌ التنسيق خاطئ، يرجى كتابة الـ ID ثم مسافة ثم عدد النقاط.")

def process_sub_all(message):
    try:
        pts = int(message.text)
        for u in users:
            users[u]['points'] = max(0, users[u]['points'] - pts) # قفل الحماية: يثبت عند 0 ولا يذهب للسالب
        save_users()
        bot.send_message(DEVELOPER_ID, f"✅ بنجاح، تم خصم {pts} نقطة من جميع المشتركين.")
    except: bot.send_message(DEVELOPER_ID, "❌ أرسل قيمة رقمية صحيحة فقط.")

bot.infinity_polling()
