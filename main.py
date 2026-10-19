import os
import sqlite3
import threading
import telebot
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# 1. خادم ويب لتشغيل البوت على Render
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running online!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 2. إعدادات البوت والقيم الأساسية
# ==========================================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_USER_ID", "0")

if not TOKEN:
    raise RuntimeError("يجب إعداد TELEGRAM_BOT_TOKEN في Secrets.")

ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 0

bot = telebot.TeleBot(TOKEN)

DB_FILE = "library.db"

SUBJECTS = [
    "مهارة اللغة العربية",
    "مهارة اللغة الإنجليزية",
    "التفاضل والتكامل",
    "الفيزياء العامة وحوسبة",
    "مقدمة في الحوسبة",
    "مهارات الحاسوب"
]

CATEGORIES = [
    "المحاضرات",
    "شروحات فيديو",
    "التكاليف",
    "ملفات PDF",
    "الملحقات"
]

HOME_ITEMS = [
    "📚 المواد التعليمية",
    "📎 الملحقات",
    "📅 الجدول الدراسي",
    "❓ طرح السؤال",
    "💬 متابعة السؤال",
    "🔔 التذكيرات",
    "👨‍💻 مطور البوت"
]

user_states = {}
user_data = {}

# ==========================================
# 3. قاعدة البيانات
# ==========================================
def connect_db():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                category TEXT NOT NULL,
                doctor TEXT DEFAULT '',
                title TEXT NOT NULL,
                notes TEXT DEFAULT '',
                content_type TEXT NOT NULL,
                file_id TEXT DEFAULT '',
                text_content TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT DEFAULT '',
                question TEXT NOT NULL,
                answer TEXT DEFAULT '',
                status TEXT DEFAULT 'قيد المراجعة',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

init_db()

# ==========================================
# 4. الواجهات والقوائم
# ==========================================
def make_reply_keyboard(items, columns=2):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=columns)
    for i in range(0, len(items), columns):
        markup.row(*[KeyboardButton(x) for x in items[i:i + columns]])
    return markup

def send_home(chat_id):
    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)
    bot.send_message(
        chat_id,
        "🎓 **كلية تكنولوجيا المعلومات**\n"
        "💻 **قسم تكنولوجيا المعلومات (IT) - موازي**\n\n"
        "اختر الخدمة التي تريدها:",
        reply_markup=make_reply_keyboard(HOME_ITEMS)
    )

def is_admin(user_id):
    return ADMIN_ID == 0 or user_id == ADMIN_ID

def get_subjects_inline(prefix="sub"):
    markup = InlineKeyboardMarkup()
    icons = ["📖 ", "📖 ", "📐 ", "⚛️ ", "💻 ", "💻 "]
    for idx, sub in enumerate(SUBJECTS):
        icon = icons[idx] if idx < len(icons) else "📚 "
        markup.add(InlineKeyboardButton(f"{icon}{sub}", callback_data=f"{prefix}_{idx}"))
    markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
    return markup

def get_categories_inline(prefix="cat"):
    markup = InlineKeyboardMarkup()
    cat_icons = {
        "المحاضرات": "📖 ",
        "شروحات فيديو": "🎥 ",
        "التكاليف": "📝 ",
        "ملفات PDF": "📄 ",
        "الملحقات": "📎 "
    }
    for cat in CATEGORIES:
        icon = cat_icons.get(cat, "📂 ")
        markup.add(InlineKeyboardButton(f"{icon}{cat}", callback_data=f"{prefix}_{cat}"))
    markup.add(InlineKeyboardButton("🔄 رجوع للمواد", callback_data="back_to_subjects"))
    markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
    return markup

# ==========================================
# 5. أوامر لوحة الإدارة
# ==========================================
@bot.message_handler(commands=["start"])
def start(message):
    send_home(message.chat.id)

@bot.message_handler(commands=["admin"])
@bot.message_handler(func=lambda m: m.text is not None and m.text.strip().lower() in ["admin", "ادمن"])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ ليس لديك صلاحية دخول لوحة الإدارة.")
        return

    user_states[message.chat.id] = "admin_menu"
    bot.send_message(
        message.chat.id,
        "🔐 **لوحة إدارة مكتبة الكلية**\n\nاختر العملية المطلوبة:",
        reply_markup=make_reply_keyboard([
            "➕ إضافة محتوى",
            "💬 أسئلة الطلاب",
            "🏠 القائمة الرئيسية"
        ])
    )

def ask_admin_field(chat_id, field):
    prompts = {
        "doctor": "👨‍🏫 **اكتب اسم الدكتور:**\n(إذا لم يوجد، أرسل: لا يوجد)",
        "title": "📝 **اكتب اسم المحاضرة التي سيندرج تحتها المحتوى:**\n(مثال: المحاضرة الأولى، المحاضرة الثانية...)",
        "notes": "📌 **اكتب الملاحظات:**\n(إذا لم يوجد، أرسل: لا يوجد)",
        "payload": "📎 **أرسل المحتوى الآن:**\n(ملف PDF، فيديو، صورة، رابط، نص، أو تسجيل صوتي)"
    }
    user_states[chat_id] = "admin_add_" + field
    bot.send_message(chat_id, prompts[field])

def save_content_db(chat_id, content_type, file_id="", text_content=""):
    data = user_data.get(chat_id, {})
    with connect_db() as conn:
        conn.execute("""
            INSERT INTO content (
                subject, category, doctor, title, notes, content_type, file_id, text_content
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("subject", "عام"),
            data.get("category", "المحاضرات"),
            data.get("doctor", ""),
            data.get("title", "المحاضرة الأولى"),
            data.get("notes", ""),
            content_type,
            file_id,
            text_content
        ))

    bot.send_message(
        chat_id,
        "✅ **تم الحفظ والربط بنجاح!**\n\n"
        f"📚 **المادة:** {data.get('subject')}\n"
        f"📖 **المحاضرة:** {data.get('title')}\n"
        f"📂 **النوع/القسم:** {data.get('category')}\n"
        f"👨‍🏫 **الدكتور:** {data.get('doctor') or 'غير محدد'}\n\n"
        "تم ربط هذا المحتوى بالمحاضرة بنجاح ويمكن للطلاب التوصل إليه الآن.",
        reply_markup=make_reply_keyboard(HOME_ITEMS)
    )
    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)

@bot.message_handler(
    content_types=["text", "document", "video", "photo", "audio", "voice", "animation", "video_note"],
    func=lambda m: user_states.get(m.chat.id) == "admin_add_payload"
)
def receive_payload(message):
    if not is_admin(message.from_user.id):
        return

    if message.content_type == "text":
        save_content_db(message.chat.id, "text", text_content=message.text)
        return

    file_id = ""
    if message.content_type == "photo":
        file_id = message.photo[-1].file_id
    elif message.content_type == "document":
        file_id = message.document.file_id
    elif message.content_type == "video":
        file_id = message.video.file_id
    elif message.content_type == "audio":
        file_id = message.audio.file_id
    elif message.content_type == "voice":
        file_id = message.voice.file_id
    elif message.content_type == "animation":
        file_id = message.animation.file_id
    elif message.content_type == "video_note":
        file_id = message.video_note.file_id

    save_content_db(message.chat.id, message.content_type, file_id=file_id)

# ==========================================
# 6. الأزرار التفاعلية (Callback Query)
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "go_home":
        send_home(chat_id)
        bot.answer_callback_query(call.id)
        return

    # --- خطوات الإضافة للأدمن ---
    if data.startswith("admin_sub_"):
        sub_idx = int(data.split("_")[2])
        subject_name = SUBJECTS[sub_idx]
        user_data.setdefault(chat_id, {})["subject"] = subject_name
        
        bot.edit_message_text(
            f"➕ **المادة المختارة:** {subject_name}\nاختر القسم الذي يتبع له هذا المرفق:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=get_categories_inline("admin_cat")
        )
        bot.answer_callback_query(call.id)
        return

    if data.startswith("admin_cat_"):
        category_name = data.replace("admin_cat_", "")
        user_data.setdefault(chat_id, {})["category"] = category_name
        
        bot.send_message(
            chat_id,
            f"🎯 **إدخال بيانات المحاضرة:**\n📚 المادة: {user_data[chat_id]['subject']}\n📂 القسم: {category_name}"
        )
        ask_admin_field(chat_id, "doctor")
        bot.answer_callback_query(call.id)
        return

    # --- تصفح الطلاب ---
    if data.startswith("sub_"):
        sub_idx = int(data.split("_")[1])
        subject_name = SUBJECTS[sub_idx]
        user_data.setdefault(chat_id, {})["subject"] = subject_name
        
        bot.edit_message_text(
            f"📚 **{subject_name}**\nاختر القسم المطلوب:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=get_categories_inline("cat")
        )
        bot.answer_callback_query(call.id)
        return

    if data == "back_to_subjects":
        bot.edit_message_text(
            "📚 اختر المادة التعليمية:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=get_subjects_inline("sub")
        )
        bot.answer_callback_query(call.id)
        return

    # عرض قائمة المحاضرات التابعة للمادة وقسم التصفح
    if data.startswith("cat_"):
        category_name = data.replace("cat_", "")
        user_data.setdefault(chat_id, {})["category"] = category_name
        subject = user_data.get(chat_id, {}).get("subject", "عام")

        with connect_db() as conn:
            rows = conn.execute("""
                SELECT DISTINCT title FROM content
                WHERE subject = ?
                ORDER BY id ASC
            """, (subject,)).fetchall()

        if not rows:
            back_cats_markup = InlineKeyboardMarkup()
            back_cats_markup.add(InlineKeyboardButton("🔄 رجوع للأقسام", callback_data="back_to_cats"))
            back_cats_markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
            
            bot.edit_message_text(
                f"📂 **{category_name}** - {subject}\n\n⏳ **سوف يتم إدراج المحاضرات والمحتويات قريباً.**",
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=back_cats_markup
            )
            bot.answer_callback_query(call.id)
            return

        markup = InlineKeyboardMarkup()
        for row in rows:
            markup.add(InlineKeyboardButton(f"📖 {row['title']}", callback_data=f"lec_{row['title']}"))
        
        markup.add(InlineKeyboardButton("🔄 رجوع للأقسام", callback_data="back_to_cats"))
        markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))

        bot.edit_message_text(
            f"📚 **{subject}**\nاختر المحاضرة المطلوبة لعرض محتوياتها:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
        return

    if data == "back_to_cats":
        subject = user_data.get(chat_id, {}).get("subject", "عام")
        bot.edit_message_text(
            f"📚 **{subject}**\nاختر القسم المطلوب:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=get_categories_inline("cat")
        )
        bot.answer_callback_query(call.id)
        return

    # عند النقر على محاضرة معينة (مثلاً المحاضرة الأولى)، يتم استعراض الأقسام المدرجة تحت هذه المحاضرة
    if data.startswith("lec_"):
        lecture_title = data.replace("lec_", "")
        user_data.setdefault(chat_id, {})["current_lecture"] = lecture_title
        subject = user_data.get(chat_id, {}).get("subject", "عام")

        with connect_db() as conn:
            available_cats = conn.execute("""
                SELECT DISTINCT category FROM content
                WHERE subject = ? AND title = ?
            """, (subject, lecture_title)).fetchall()

        cat_names = [r["category"] for r in available_cats]

        markup = InlineKeyboardMarkup()
        cat_icons = {
            "المحاضرات": "📄 ملف المحاضرة (PDF/نص)",
            "شروحات فيديو": "🎥 فيديو الشرح",
            "التكاليف": "📝 التكليف",
            "ملفات PDF": "📄 ملفات PDF أخرى",
            "الملحقات": "📎 الملحقات"
        }

        # إظهار الخيارات المتاحة والمربوطة بالمحاضرة فقط
        for c_name in CATEGORIES:
            if c_name in cat_names:
                btn_text = cat_icons.get(c_name, c_name)
                markup.add(InlineKeyboardButton(btn_text, callback_data=f"showcontent_{c_name}"))

        markup.add(InlineKeyboardButton("🔄 رجوع لقائمة المحاضرات", callback_data=f"cat_المحاضرات"))
        markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))

        bot.edit_message_text(
            f"📖 **{lecture_title}** ({subject})\nاختر المحتوى الذي تريد عرضه لهذه المحاضرة:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
        return

    # عرض محتوى قسم معين داخل المحاضرة المحددة
    if data.startswith("showcontent_"):
        category_name = data.replace("showcontent_", "")
        subject = user_data.get(chat_id, {}).get("subject", "عام")
        lecture_title = user_data.get(chat_id, {}).get("current_lecture", "المحاضرة الأولى")

        with connect_db() as conn:
            items = conn.execute("""
                SELECT * FROM content
                WHERE subject = ? AND title = ? AND category = ?
                ORDER BY id ASC
            """, (subject, lecture_title, category_name)).fetchall()

        if not items:
            bot.answer_callback_query(call.id, "لا توجد محتويات مدرجة في هذا القسم لهذه المحاضرة.")
            return

        back_markup = InlineKeyboardMarkup()
        back_markup.add(InlineKeyboardButton("🔙 رجوع للمحاضرة", callback_data=f"lec_{lecture_title}"))

        for idx, item in enumerate(items):
            text = f"📖 **{item['title']}**\n📚 **المادة:** {item['subject']}\n📂 **القسم:** {item['category']}\n"
            if item["doctor"]:
                text += f"👨‍🏫 **الدكتور:** {item['doctor']}\n"
            if item["notes"]:
                text += f"📌 **ملاحظات:** {item['notes']}\n"

            current_markup = back_markup if idx == len(items) - 1 else None

            ctype = item["content_type"]
            if ctype == "text":
                bot.send_message(chat_id, text + "\n" + item["text_content"], reply_markup=current_markup)
            elif ctype == "document":
                bot.send_document(chat_id, item["file_id"], caption=text, reply_markup=current_markup)
            elif ctype == "video":
                bot.send_video(chat_id, item["file_id"], caption=text, reply_markup=current_markup)
            elif ctype == "photo":
                bot.send_photo(chat_id, item["file_id"], caption=text, reply_markup=current_markup)
            elif ctype == "audio":
                bot.send_audio(chat_id, item["file_id"], caption=text, reply_markup=current_markup)
            elif ctype == "voice":
                bot.send_voice(chat_id, item["file_id"])
                bot.send_message(chat_id, text, reply_markup=current_markup)

        bot.answer_callback_query(call.id)
        return

# ==========================================
# 7. المعالج الرئيسي للرسائل
# ==========================================
@bot.message_handler(func=lambda m: m.text is not None and not m.text.startswith("/"))
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if text in ("📚 المواد التعليمية", "📚 المواد الدراسية"):
        bot.send_message(
            chat_id,
            "📚 اختر المادة التعليمية:",
            reply_markup=get_subjects_inline("sub")
        )
        return

    elif text == "📎 الملحقات":
        bot.send_message(chat_id, "📎 قسم الملحقات والتنصيبات العامة:\nسوف يتم رفعه قريباً.")
        return

    elif text == "📅 الجدول الدراسي":
        bot.send_message(chat_id, "📅 الجدول الدراسي:\nسوف يتم رفعه قريباً.")
        return

    elif text == "🔔 التذكيرات":
        bot.send_message(chat_id, "🔔 قسم التذكيرات الهامة:\nلا توجد تذكيرات جديدة حالياً.")
        return

    elif text == "❓ طرح السؤال":
        user_states[chat_id] = "ask_question"
        bot.send_message(chat_id, "اكتب سؤالك الآن وسوف يتم إرساله للرد عليه:")
        return

    elif text == "💬 متابعة السؤال":
        bot.send_message(chat_id, "لا توجد أسئلة سابقة مسجلة.")
        return

    elif text == "👨‍💻 مطور البوت":
        bot.send_message(
            chat_id,
            "👨‍💻 **مطور البوت:**\n"
            "المهندس / محمد الظاهر\n"
            "📞 **رقم التواصل:** `718117501`\n\n"
            "مخصص لخدمة طلاب كلية تكنولوجيا المعلومات - قسم (IT) موازي بجامعة إقليم سبأ.",
            parse_mode="Markdown"
        )
        return

    state = user_states.get(chat_id)

    if state == "admin_add_doctor":
        user_data[chat_id]["doctor"] = "" if text == "لا يوجد" else text
        ask_admin_field(chat_id, "title")
        return

    if state == "admin_add_title":
        user_data[chat_id]["title"] = text
        ask_admin_field(chat_id, "notes")
        return

    if state == "admin_add_notes":
        user_data[chat_id]["notes"] = "" if text == "لا يوجد" else text
        ask_admin_field(chat_id, "payload")
        return

    if state == "admin_menu":
        if text == "➕ إضافة محتوى":
            user_data[chat_id] = {}
            bot.send_message(
                chat_id,
                "📚 **اختر المادة التي تريد إضافة محتوى إليها:**",
                reply_markup=get_subjects_inline("admin_sub")
            )
        elif text == "🏠 القائمة الرئيسية":
            send_home(chat_id)
        return

def start_bot():
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()
    run_flask()