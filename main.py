import os
import sqlite3
import threading
import time
import telebot

from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ==========================================
# إعدادات البوت
# ==========================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_USER_ID", "")

if not TOKEN:
    raise RuntimeError("يجب إعداد TELEGRAM_BOT_TOKEN في Secrets.")

if not ADMIN_ID.isdigit():
    raise RuntimeError("يجب إعداد ADMIN_USER_ID برقم حساب المدير.")

ADMIN_ID = int(ADMIN_ID)

bot = telebot.TeleBot(TOKEN)

DB_FILE = "library.db"

SYSTEM = "الموازي"

SUBJECTS = [
    "التفاضل والتكامل",
    "اللغة العربية",
    "اللغة الإنجليزية",
    "مقدمة في تقنية المعلومات",
    "أساسيات الحاسوب",
    "البرمجة",
    "رياضيات",
    "فيزياء",
    "مادة أخرى"
]

CATEGORIES = [
    "المحاضرات",
    "فيديوهات الشرح",
    "ملفات PDF",
    "التكاليف والواجبات",
    "الملخصات",
    "الاختبارات",
    "الملحقات",
    "التذكيرات",
    "أخرى"
]

HOME_ITEMS = [
    "📚 المواد الدراسية",
    "📎 الملحقات",
    "📅 الجدول الدراسي",
    "❓ طرح السؤال",
    "💬 متابعة السؤال",
    "🔔 التذكيرات"
]

# حالة المستخدم أثناء تنفيذ الخطوات
user_states = {}
user_data = {}


# ==========================================
# قاعدة البيانات
# ==========================================

def connect_db():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                semester TEXT NOT NULL,
                system TEXT NOT NULL DEFAULT 'الموازي',
                UNIQUE(name, semester, system)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                semester TEXT NOT NULL,
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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                semester TEXT NOT NULL,
                subject TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # إضافة المواد الافتراضية للفصلين
        for semester in (
            "الفصل الدراسي الأول",
            "الفصل الدراسي الثاني"
        ):
            for subject in SUBJECTS:
                conn.execute("""
                    INSERT OR IGNORE INTO subjects
                    (name, semester, system)
                    VALUES (?, ?, ?)
                """, (subject, semester, SYSTEM))


init_db()


# ==========================================
# القوائم
# ==========================================

def make_keyboard(items, columns=2):
    markup = ReplyKeyboardMarkup(
        resize_keyboard=True,
        row_width=columns
    )

    for i in range(0, len(items), columns):
        markup.row(*[
            KeyboardButton(x)
            for x in items[i:i + columns]
        ])

    return markup


def send_home(chat_id):
    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)

    bot.send_message(
        chat_id,
        "🎓 مرحباً بك في مكتبة طلاب تقنية المعلومات "
        "بجامعة إقليم سبأ.\n\n"
        "اختر الخدمة التي تريدها:",
        reply_markup=make_keyboard(HOME_ITEMS)
    )


def send_semesters(chat_id, purpose):
    user_states[chat_id] = purpose

    bot.send_message(
        chat_id,
        "📅 اختر الفصل الدراسي:",
        reply_markup=make_keyboard([
            "الفصل الدراسي الأول",
            "الفصل الدراسي الثاني",
            "⬅️ رجوع للقائمة"
        ])
    )


def get_subjects(semester):
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT name FROM subjects
            WHERE semester = ? AND system = ?
            ORDER BY name
        """, (semester, SYSTEM)).fetchall()

    return [row["name"] for row in rows]


def show_subjects(chat_id, semester, purpose):
    subjects = get_subjects(semester)

    user_data.setdefault(chat_id, {})
    user_data[chat_id]["semester"] = semester
    user_states[chat_id] = purpose

    buttons = subjects + ["⬅️ رجوع للقائمة"]

    bot.send_message(
        chat_id,
        "📚 اختر المادة الدراسية:",
        reply_markup=make_keyboard(buttons)
    )


def show_categories(chat_id, purpose):
    user_states[chat_id] = purpose

    bot.send_message(
        chat_id,
        "📂 اختر القسم المطلوب:",
        reply_markup=make_keyboard(
            CATEGORIES + ["⬅️ رجوع للمواد"]
        )
    )


def is_admin(message):
    return message.from_user.id == ADMIN_ID


def is_admin_id(user_id):
    return user_id == ADMIN_ID


# ==========================================
# بدء البوت
# ==========================================

@bot.message_handler(commands=["start"])
def start(message):
    send_home(message.chat.id)


# ==========================================
# لوحة الإدارة
# ==========================================

@bot.message_handler(
    func=lambda m: m.text is not None
    and m.text.strip().lower() == "admin"
)
def admin_panel(message):
    if not is_admin(message):
        bot.send_message(
            message.chat.id,
            "⛔ ليس لديك صلاحية دخول لوحة الإدارة."
        )
        return

    user_states[message.chat.id] = "admin_menu"

    bot.send_message(
        message.chat.id,
        "🔐 لوحة إدارة مكتبة الجامعة\n\n"
        "اختر العملية المطلوبة:",
        reply_markup=make_keyboard([
            "➕ إضافة محتوى",
            "➕ إضافة مادة",
            "📋 عرض المحتوى",
            "🗑 حذف محتوى",
            "💬 أسئلة الطلاب",
            "🏠 القائمة الرئيسية"
        ])
    )


# ==========================================
# بدء إضافة المحتوى
# ==========================================

def begin_add_content(chat_id):
    user_data[chat_id] = {}
    send_semesters(chat_id, "admin_choose_semester")


def ask_next_content_field(chat_id, field):
    prompts = {
        "doctor": "👨‍🏫 اكتب اسم الدكتور.\n"
                  "إذا لم يوجد، اكتب: لا يوجد",
        "subject": "📚 اكتب اسم المادة الدراسية:",
        "title": "📝 اكتب عنوان المحاضرة أو المحتوى:",
        "notes": "📌 اكتب الملاحظات، أو اكتب: لا يوجد",
        "payload": (
            "📎 أرسل المحتوى الآن.\n\n"
            "يمكنك إرسال ملف أو فيديو أو صورة أو نص أو رابط."
        )
    }

    user_states[chat_id] = "add_" + field

    bot.send_message(chat_id, prompts[field])


def begin_add_payload(chat_id):
    ask_next_content_field(chat_id, "payload")


def save_content(chat_id, content_type, file_id="", text_content=""):
    data = user_data.get(chat_id, {})

    with connect_db() as conn:
        conn.execute("""
            INSERT INTO content (
                semester, subject, category, doctor,
                title, notes, content_type, file_id, text_content
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["semester"],
            data["subject"],
            data["category"],
            data.get("doctor", ""),
            data["title"],
            data.get("notes", ""),
            content_type,
            file_id,
            text_content
        ))

    bot.send_message(
        chat_id,
        "✅ تمت إضافة المحتوى بنجاح!\n\n"
        f"📚 المادة: {data['subject']}\n"
        f"📂 القسم: {data['category']}\n"
        f"📝 العنوان: {data['title']}\n\n"
        "أصبح المحتوى محفوظاً في المكتبة."
    )

    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)


# ==========================================
# إرسال المحتوى للطلاب
# ==========================================

def send_saved_content(chat_id, item):
    text = (
        f"📚 المادة: {item['subject']}\n"
        f"📂 القسم: {item['category']}\n"
        f"📝 العنوان: {item['title']}\n"
    )

    if item["doctor"]:
        text += f"👨‍🏫 الدكتور: {item['doctor']}\n"

    if item["notes"]:
        text += f"📌 ملاحظات: {item['notes']}\n"

    content_type = item["content_type"]
    file_id = item["file_id"]
    text_content = item["text_content"]

    if content_type == "text":
        bot.send_message(
            chat_id,
            text + "\n" + text_content
        )

    elif content_type == "document":
        bot.send_document(
            chat_id, file_id, caption=text
        )

    elif content_type == "video":
        bot.send_video(
            chat_id, file_id, caption=text
        )

    elif content_type == "photo":
        bot.send_photo(
            chat_id, file_id, caption=text
        )

    elif content_type == "audio":
        bot.send_audio(
            chat_id, file_id, caption=text
        )

    elif content_type == "animation":
        bot.send_animation(
            chat_id, file_id, caption=text
        )

    elif content_type == "voice":
        bot.send_voice(chat_id, file_id)
        bot.send_message(chat_id, text)

    elif content_type == "video_note":
        bot.send_video_note(chat_id, file_id)
        bot.send_message(chat_id, text)

    else:
        bot.send_message(
            chat_id,
            text + "\n" + text_content
        )


# ==========================================
# الأسئلة ومتابعتها
# ==========================================

def save_question(message):
    chat_id = message.chat.id

    question = message.text or ""

    with connect_db() as conn:
        cursor = conn.execute("""
            INSERT INTO questions
            (user_id, username, question)
            VALUES (?, ?, ?)
        """, (
            message.from_user.id,
            message.from_user.username or "",
            question
        ))

        question_id = cursor.lastrowid

    bot.send_message(
        chat_id,
        f"✅ تم إرسال سؤالك.\n"
        f"رقم السؤال: {question_id}\n"
        "يمكنك متابعة حالته من زر «متابعة السؤال»."
    )

    bot.send_message(
        ADMIN_ID,
        f"❓ سؤال جديد رقم {question_id}\n"
        f"من المستخدم: {message.from_user.id}\n"
        f"اسم المستخدم: @{message.from_user.username or 'غير محدد'}\n\n"
        f"{question}\n\n"
        f"للرد اكتب:\n"
        f"رد {question_id} ثم مسافة ثم نص الإجابة."
    )

    user_states.pop(chat_id, None)


@bot.message_handler(
    func=lambda m: m.text is not None
    and m.text.startswith("رد ")
)
def admin_answer(message):
    if not is_admin(message):
        return

    parts = message.text.split(maxsplit=2)

    if len(parts) < 3 or not parts[1].isdigit():
        bot.reply_to(
            message,
            "الصيغة الصحيحة:\nرد رقم_السؤال نص_الإجابة"
        )
        return

    question_id = int(parts[1])
    answer = parts[2]

    with connect_db() as conn:
        row = conn.execute("""
            SELECT user_id FROM questions WHERE id = ?
        """, (question_id,)).fetchone()

        if row is None:
            bot.reply_to(message, "لم أجد هذا السؤال.")
            return

        conn.execute("""
            UPDATE questions
            SET answer = ?, status = ?
            WHERE id = ?
        """, (answer, "تمت الإجابة", question_id))

    bot.send_message(
        row["user_id"],
        f"💬 تمت الإجابة عن سؤالك رقم {question_id}:\n\n"
        f"{answer}"
    )

    bot.reply_to(message, "✅ تم إرسال الإجابة للطالب.")


def show_my_questions(message):
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT id, question, answer, status
            FROM questions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 15
        """, (message.from_user.id,)).fetchall()

    if not rows:
        bot.send_message(
            message.chat.id,
            "ليس لديك أسئلة مسجلة حتى الآن."
        )
        return

    for row in rows:
        text = (
            f"❓ السؤال رقم {row['id']}\n"
            f"{row['question']}\n\n"
            f"الحالة: {row['status']}"
        )

        if row["answer"]:
            text += f"\n\n💬 الإجابة:\n{row['answer']}"

        bot.send_message(message.chat.id, text)


# ==========================================
# استقبال الملفات والنصوص
# ==========================================

@bot.message_handler(
    content_types=[
        "text", "document", "video", "photo",
        "audio", "voice", "animation", "video_note"
    ],
    func=lambda m: (
        m.chat.id in user_states
        and user_states[m.chat.id] == "add_payload"
    )
)
def receive_content(message):
    if not is_admin(message):
        return

    if message.content_type == "text":
        save_content(
            message.chat.id,
            "text",
            text_content=message.text
        )
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

    save_content(
        message.chat.id,
        message.content_type,
        file_id=file_id
    )


# ==========================================
# إضافة مادة جديدة
# ==========================================

def add_subject_name(message):
    if not is_admin(message):
        return

    name = (message.text or "").strip()
    chat_id = message.chat.id
    semester = user_data.get(chat_id, {}).get("semester")

    if not name or not semester:
        bot.send_message(chat_id, "تعذر إضافة المادة.")
        return

    try:
        with connect_db() as conn:
            conn.execute("""
                INSERT INTO subjects (name, semester, system)
                VALUES (?, ?, ?)
            """, (name, semester, SYSTEM))

        bot.send_message(
            chat_id,
            f"✅ تمت إضافة مادة {name} إلى {semester}."
        )

    except sqlite3.IntegrityError:
        bot.send_message(
            chat_id,
            "هذه المادة موجودة بالفعل في هذا الفصل."
        )

    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)


# ==========================================
# عرض المحتوى وحذفه
# ==========================================

def list_content(chat_id):
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT id, subject, category, title
            FROM content
            ORDER BY id DESC
            LIMIT 30
        """).fetchall()

    if not rows:
        bot.send_message(chat_id, "لا يوجد محتوى محفوظ.")
        return

    for row in rows:
        bot.send_message(
            chat_id,
            f"رقم المحتوى: {row['id']}\n"
            f"المادة: {row['subject']}\n"
            f"القسم: {row['category']}\n"
            f"العنوان: {row['title']}"
        )


def delete_content_by_id(message):
    if not is_admin(message):
        return

    value = (message.text or "").strip()

    if not value.isdigit():
        bot.send_message(
            message.chat.id,
            "أرسل رقم المحتوى الذي تريد حذفه."
        )
        return

    with connect_db() as conn:
        cursor = conn.execute(
            "DELETE FROM content WHERE id = ?",
            (int(value),)
        )

    if cursor.rowcount:
        bot.send_message(message.chat.id, "✅ تم حذف المحتوى.")
    else:
        bot.send_message(message.chat.id, "لم يتم العثور على المحتوى.")

    user_states.pop(message.chat.id, None)


# ==========================================
# معالج القوائم الرئيسي
# ==========================================

@bot.message_handler(
    func=lambda m: m.text is not None
    and not m.text.startswith("/")
)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if text.lower() == "admin":
        return

    state = user_states.get(chat_id)

    # حقول إضافة المحتوى
    if state == "add_doctor":
        user_data[chat_id]["doctor"] = (
            "" if text == "لا يوجد" else text
        )
        ask_next_content_field(chat_id, "subject")
        return

    if state == "add_subject":
        user_data[chat_id]["subject"] = text
        ask_next_content_field(chat_id, "title")
        return

    if state == "add_title":
        user_data[chat_id]["title"] = text
        ask_next_content_field(chat_id, "notes")
        return

    if state == "add_notes":
        user_data[chat_id]["notes"] = (
            "" if text == "لا يوجد" else text
        )
        begin_add_payload(chat_id)
        return

    if state == "new_subject_name":
        add_subject_name(message)
        return

    if state == "delete_content":
        delete_content_by_id(message)
        return

    if state == "ask_question":
        save_question(message)
        return

    # لوحة الإدارة
    if state == "admin_menu":
        if not is_admin(message):
            return

        if text == "➕ إضافة محتوى":
            begin_add_content(chat_id)

        elif text == "➕ إضافة مادة":
            user_data[chat_id] = {}
            send_semesters(chat_id, "admin_new_subject_semester")

        elif text == "📋 عرض المحتوى":
            list_content(chat_id)

        elif text == "🗑 حذف محتوى":
            user_states[chat_id] = "delete_content"
            bot.send_message(
                chat_id,
                "أرسل رقم المحتوى الذي تريد حذفه."
            )

        elif text == "💬 أسئلة الطلاب":
            with connect_db() as conn:
                rows = conn.execute("""
                    SELECT id, user_id, question, status
                    FROM questions
                    ORDER BY id DESC
                    LIMIT 20
                """).fetchall()

            if not rows:
                bot.send_message(chat_id, "لا توجد أسئلة.")
            else:
                for row in rows:
                    bot.send_message(
                        chat_id,
                        f"السؤال رقم: {row['id']}\n"
                        f"الطالب: {row['user_id']}\n"
                        f"الحالة: {row['status']}\n\n"
                        f"{row['question']}\n\n"
                        f"للرد:\nرد {row['id']} نص الإجابة"
                    )

        elif text == "🏠 القائمة الرئيسية":
            send_home(chat_id)

        return

    # اختيار الفصل الدراسي
    if state in (
        "student_semester",
        "student_attachments_semester",
        "student_schedule_semester",
        "student_reminders_semester",
        "admin_choose_semester",
        "admin_new_subject_semester"
    ):
        if text == "⬅️ رجوع للقائمة":
            send_home(chat_id)
            return

        if text not in (
            "الفصل الدراسي الأول",
            "الفصل الدراسي الثاني"
        ):
            bot.send_message(chat_id, "اختر أحد الفصلين من القائمة.")
  