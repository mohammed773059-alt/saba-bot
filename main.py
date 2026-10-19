import os
import sqlite3
import threading
import logging
import telebot
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# 1. إعداد التسجيل
# ==========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 2. إعداد خادم الويب لـ Render
# ==========================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running online!"


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)


# ==========================================
# 3. إعدادات البوت
# ==========================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_USER_ID", "0")

if not TOKEN:
    raise RuntimeError(
        "يجب إعداد TELEGRAM_BOT_TOKEN في متغيرات البيئة."
    )

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except (ValueError, TypeError):
    ADMIN_ID = 0

bot = telebot.TeleBot(TOKEN)

DB_FILE = "library.db"

# ==========================================
# 4. المواد والأقسام
# ==========================================

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

ADMIN_MENU_ITEMS = [
    "➕ إضافة محتوى",
    "📅 رفع الجدول الدراسي",
    "💬 أسئلة الطلاب",
    "🏠 القائمة الرئيسية"
]

ADMIN_AFTER_SAVE_ITEMS = [
    "➕ إضافة محتوى آخر",
    "⚙️ لوحة الإدارة",
    "🏠 القائمة الرئيسية"
]

user_states = {}
user_data = {}

# ==========================================
# 5. قاعدة البيانات
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
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                content_type TEXT,
                file_id TEXT,
                text_content TEXT
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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reminder TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


init_db()

# ==========================================
# 6. الأدوات المساعدة
# ==========================================

def make_reply_keyboard(items, columns=2):
    markup = ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=columns
    )

    for i in range(0, len(items), columns):
        markup.row(*[
            KeyboardButton(item)
            for item in items[i:i + columns]
        ])

    return markup


def is_admin(user_id):
    return ADMIN_ID != 0 and user_id == ADMIN_ID


def send_home(chat_id):
    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)

    bot.send_message(
        chat_id,
        "🎓 كلية تكنولوجيا المعلومات\n"
        "💻 قسم تكنولوجيا المعلومات (IT) - موازي\n\n"
        "اختر الخدمة التي تريدها:",
        reply_markup=make_reply_keyboard(HOME_ITEMS)
    )


def get_subjects_inline(prefix="sub"):
    markup = InlineKeyboardMarkup()

    icons = ["📖 ", "📖 ", "📐 ", "⚛️ ", "💻 ", "💻 "]

    for idx, subject in enumerate(SUBJECTS):
        icon = icons[idx] if idx < len(icons) else "📚 "

        markup.add(
            InlineKeyboardButton(
                icon + subject,
                callback_data=f"{prefix}_{idx}"
            )
        )

    markup.add(
        InlineKeyboardButton(
            "🏠 القائمة الرئيسية",
            callback_data="go_home"
        )
    )

    return markup


def get_categories_inline(prefix="cat"):
    markup = InlineKeyboardMarkup()

    icons = {
        "المحاضرات": "📖 ",
        "شروحات فيديو": "🎥 ",
        "التكاليف": "📝 ",
        "ملفات PDF": "📄 ",
        "الملحقات": "📎 "
    }

    for category in CATEGORIES:
        markup.add(
            InlineKeyboardButton(
                icons.get(category, "📂 ") + category,
                callback_data=f"{prefix}_{category}"
            )
        )

    markup.add(
        InlineKeyboardButton(
            "🔄 رجوع للمواد",
            callback_data="back_to_subjects"
        )
    )

    markup.add(
        InlineKeyboardButton(
            "🏠 القائمة الرئيسية",
            callback_data="go_home"
        )
    )

    return markup


def safe_edit(call, text, reply_markup=None):
    try:
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=reply_markup
        )


def show_content(chat_id, row):
    content_type = row["content_type"]
    file_id = row["file_id"]
    text_content = row["text_content"]

    caption = (
        f"📚 المادة: {row['subject']}\n"
        f"📖 العنوان: {row['title']}\n"
        f"📂 القسم: {row['category']}\n"
        f"👨‍🏫 الدكتور: {row['doctor'] or 'غير محدد'}\n"
        f"📌 الملاحظات: {row['notes'] or 'لا توجد'}"
    )

    try:
        if content_type == "text":
            bot.send_message(
                chat_id,
                caption + "\n\n" + text_content
            )

        elif content_type == "photo":
            bot.send_photo(
                chat_id,
                file_id,
                caption=caption
            )

        elif content_type == "document":
            bot.send_document(
                chat_id,
                file_id,
                caption=caption
            )

        elif content_type == "video":
            bot.send_video(
                chat_id,
                file_id,
                caption=caption
            )

        elif content_type == "audio":
            bot.send_audio(
                chat_id,
                file_id,
                caption=caption
            )

        elif content_type == "voice":
            bot.send_voice(chat_id, file_id)

        elif content_type == "animation":
            bot.send_animation(
                chat_id,
                file_id,
                caption=caption
            )

        elif content_type == "video_note":
            bot.send_video_note(chat_id, file_id)

        else:
            bot.send_message(
                chat_id,
                "⚠️ نوع المحتوى غير مدعوم للعرض."
            )

    except Exception:
        logger.exception("تعذر إرسال المحتوى")
        bot.send_message(
            chat_id,
            "تعذر عرض هذا المحتوى. حاول مرة أخرى."
        )


# ==========================================
# 7. بدء البوت والقائمة الرئيسية
# ==========================================

@bot.message_handler(commands=["start"])
def start(message):
    send_home(message.chat.id)


# ==========================================
# 8. لوحة الإدارة
# ==========================================

@bot.message_handler(commands=["admin"])
@bot.message_handler(
    func=lambda m: (
        m.text is not None
        and m.text.strip().lower() in [
            "admin",
            "ادمن",
            "⚙️ لوحة الإدارة"
        ]
    )
)
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "⛔ ليس لديك صلاحية دخول لوحة الإدارة."
        )
        return

    user_states[message.chat.id] = "admin_menu"

    bot.send_message(
        message.chat.id,
        "🔐 لوحة إدارة مكتبة الكلية\n\n"
        "اختر العملية المطلوبة:",
        reply_markup=make_reply_keyboard(ADMIN_MENU_ITEMS)
    )


def ask_admin_field(chat_id, field):
    prompts = {
        "doctor": "👨‍🏫 اكتب اسم الدكتور، أو أرسل: لا يوجد",
        "title": "📝 اكتب عنوان المحاضرة، مثال: المحاضرة الأولى",
        "notes": "📌 اكتب الملاحظات، أو أرسل: لا يوجد",
        "payload": (
            "📎 أرسل المحتوى الآن:\n"
            "ملف PDF أو فيديو أو صورة أو رابط أو نص "
            "أو تسجيل صوتي."
        )
    }

    user_states[chat_id] = "admin_add_" + field

    bot.send_message(chat_id, prompts[field])


def save_content_db(chat_id, content_type, file_id="", text_content=""):
    data = user_data.get(chat_id, {})

    with connect_db() as conn:
        conn.execute("""
            INSERT INTO content (
                subject, category, doctor, title, notes,
                content_type, file_id, text_content
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
        "✅ تم الحفظ بنجاح!\n\n"
        f"📚 المادة: {data.get('subject', 'عام')}\n"
        f"📖 المحاضرة: {data.get('title', 'المحاضرة الأولى')}\n"
        f"📂 القسم: {data.get('category', 'المحاضرات')}\n"
        f"👨‍🏫 الدكتور: {data.get('doctor') or 'غير محدد'}\n\n"
        "ماذا تريد أن تفعل الآن؟",
        reply_markup=make_reply_keyboard(ADMIN_AFTER_SAVE_ITEMS)
    )

    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)


# ==========================================
# 9. الأسئلة والإجابات
# ==========================================

def save_user_question(message):
    chat_id = message.chat.id
    question_text = message.text or ""

    with connect_db() as conn:
        cursor = conn.execute("""
            INSERT INTO questions (user_id, username, question)
            VALUES (?, ?, ?)
        """, (
            message.from_user.id,
            message.from_user.username or "بدون معرف",
            question_text
        ))

        question_id = cursor.lastrowid

    bot.send_message(
        chat_id,
        f"✅ تم إرسال سؤالك بنجاح!\n\n"
        f"🔢 رقم السؤال: {question_id}\n"
        "يمكنك الضغط على «💬 متابعة السؤال» لمعرفة الإجابة لاحقًا.",
        reply_markup=make_reply_keyboard(HOME_ITEMS)
    )

    if ADMIN_ID != 0:
        try:
            bot.send_message(
                ADMIN_ID,
                f"❓ سؤال جديد رقم: {question_id}\n"
                f"👤 الطالب: {message.from_user.first_name}\n"
                f"🆔 معرف الطالب: {message.from_user.id}\n\n"
                f"💬 نص السؤال:\n{question_text}\n\n"
                f"للرد، أرسل:\nرد {question_id} نص الإجابة"
            )
        except Exception:
            logger.exception("تعذر إرسال إشعار السؤال للمدير")

    user_states.pop(chat_id, None)


def show_user_questions(message):
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT id, question, answer, status, created_at
            FROM questions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
        """, (message.from_user.id,)).fetchall()

    if not rows:
        bot.send_message(
            message.chat.id,
            "ℹ️ ليس لديك أسئلة مسجلة حاليًا."
        )
        return

    for row in rows:
        text = (
            f"❓ السؤال رقم: {row['id']}\n"
            f"📝 سؤالك: {row['question']}\n"
            f"📌 الحالة: {row['status']}\n"
        )

        if row["answer"]:
            text += f"\n💬 الإجابة:\n{row['answer']}"

        bot.send_message(message.chat.id, text)


@bot.message_handler(
    func=lambda m: m.text is not None and m.text.startswith("رد ")
)
def reply_to_question(message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=2)

    if len(parts) < 3 or not parts[1].isdigit():
        bot.reply_to(
            message,
            "⚠️ الصيغة الصحيحة:\nرد رقم_السؤال نص الإجابة"
        )
        return

    question_id = int(parts[1])
    answer_text = parts[2]

    with connect_db() as conn:
        row = conn.execute(
            "SELECT user_id, question FROM questions WHERE id = ?",
            (question_id,)
        ).fetchone()

        if not row:
            bot.reply_to(
                message,
                "❌ لم يتم العثور على السؤال."
            )
            return

        conn.execute("""
            UPDATE questions
            SET answer = ?, status = 'تمت الإجابة'
            WHERE id = ?
        """, (answer_text, question_id))

    try:
        bot.send_message(
            row["user_id"],
            f"🔔 تمت الإجابة على سؤالك رقم ({question_id})\n\n"
            f"❓ السؤال:\n{row['question']}\n\n"
            f"💬 الإجابة:\n{answer_text}"
        )

        bot.reply_to(
            message,
            "✅ تم إرسال الإجابة إلى الطالب."
        )

    except Exception:
        bot.reply_to(
            message,
            "تم حفظ الإجابة، لكن تعذرت مراسلة الطالب."
        )


# ==========================================
# 10. استقبال المحتوى والجدول الدراسي
# ==========================================

@bot.message_handler(
    content_types=[
        "text", "document", "video", "photo",
        "audio", "voice", "animation", "video_note"
    ],
    func=lambda m: user_states.get(m.chat.id) in [
        "admin_add_payload",
        "admin_upload_schedule"
    ]
)
def receive_payload(message):
    if not is_admin(message.from_user.id):
        return

    chat_id = message.chat.id
    state = user_states.get(chat_id)
    content_type = message.content_type

    file_id = ""
    text_content = ""

    if content_type == "text":
        text_content = message.text

    elif content_type == "photo":
        file_id = message.photo[-1].file_id

    elif content_type == "document":
        file_id = message.document.file_id

    elif content_type == "video":
        file_id = message.video.file_id

    elif content_type == "audio":
        file_id = message.audio.file_id

    elif content_type == "voice":
        file_id = message.voice.file_id

    elif content_type == "animation":
        file_id = message.animation.file_id

    elif content_type == "video_note":
        file_id = message.video_note.file_id

    if state == "admin_upload_schedule":
        with connect_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO settings (
                    key, content_type, file_id, text_content
                )
                VALUES ('schedule', ?, ?, ?)
            """, (content_type, file_id, text_content))

        bot.send_message(
            chat_id,
            "✅ تم تحديث الجدول الدراسي بنجاح.",
            reply_markup=make_reply_keyboard(ADMIN_MENU_ITEMS)
        )

        user_states.pop(chat_id, None)
        return

    save_content_db(
        chat_id,
        content_type,
        file_id=file_id,
        text_content=text_content
    )


# ==========================================
# 11. معالجة الأزرار
# ==========================================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data

    try:
        if data == "go_home":
            send_home(chat_id)
            bot.answer_callback_query(call.id)
            return

        # اختيار مادة لإضافة المحتوى
        if data.startswith("admin_sub_"):
            if not is_admin(call.from_user.id):
                bot.answer_callback_query(
                    call.id,
                    "ليس لديك صلاحية.",
                    show_alert=True
                )
                return

            subject_index = int(data.split("_")[2])

            if not 0 <= subject_index < len(SUBJECTS):
                bot.answer_callback_query(call.id, "المادة غير صحيحة.")
                return

            user_data.setdefault(chat_id, {})["subject"] = (
                SUBJECTS[subject_index]
            )

            safe_edit(
                call,
                f"➕ المادة المختارة: {SUBJECTS[subject_index]}\n"
                "اختر القسم:",
                get_categories_inline("admin_cat")
            )

            bot.answer_callback_query(call.id)
            return

        # اختيار القسم أثناء الإضافة
        if data.startswith("admin_cat_"):
            if not is_admin(call.from_user.id):
                bot.answer_callback_query(
                    call.id,
                    "ليس لديك صلاحية.",
                    show_alert=True
                )
                return

            category = data.replace("admin_cat_", "", 1)

            if category not in CATEGORIES:
                bot.answer_callback_query(call.id, "القسم غير صحيح.")
                return

            user_data.setdefault(chat_id, {})["category"] = category

            bot.send_message(
                chat_id,
                f"📚 المادة: {user_data[chat_id]['subject']}\n"
                f"📂 القسم: {category}"
            )

            ask_admin_field(chat_id, "doctor")
            bot.answer_callback_query(call.id)
            return

        # اختيار مادة للعرض أو الملحقات
        if data.startswith("sub_") or data.startswith("submat_"):
            attachment_mode = data.startswith("submat_")
            subject_index = int(data.split("_")[1])

            if not 0 <= subject_index < len(SUBJECTS):
                bot.answer_callback_query(call.id, "المادة غير صحيحة.")
                return

            subject = SUBJECTS[subject_index]

            user_data.setdefault(chat_id, {})["subject"] = subject
            user_data[chat_id]["mode"] = (
                "attachments" if attachment_mode else "normal"
            )

            if attachment_mode:
                with connect_db() as conn:
                    rows = conn.execute("""
                        SELECT DISTINCT title
                        FROM content
                        WHERE subject = ?
                        ORDER BY MIN(id)
                    """, (subject,)).fetchall()

                markup = InlineKeyboardMarkup()

                if not rows:
                    markup.add(
                        InlineKeyboardButton(
                            "🔄 رجوع للمواد",
                            callback_data="back_to_attachments_subjects"
                        )
                    )
                    markup.add(
                        InlineKeyboardButton(
                            "🏠 القائمة الرئيسية",
                            callback_data="go_home"
                        )
               