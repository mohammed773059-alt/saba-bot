import os
import sqlite3
import threading
import time
import telebot
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

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

        for semester in ("الفصل الدراسي الأول", "الفصل الدراسي الثاني"):
            for subject in SUBJECTS:
                conn.execute("""
                    INSERT OR IGNORE INTO subjects (name, semester, system)
                    VALUES (?, ?, ?)
                """, (subject, semester, SYSTEM))

init_db()

# ==========================================
# 4. القوائم والواجهات
# ==========================================
def make_keyboard(items, columns=2):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=columns)
    for i in range(0, len(items), columns):
        markup.row(*[KeyboardButton(x) for x in items[i:i + columns]])
    return markup

def send_home(chat_id):
    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)
    bot.send_message(
        chat_id,
        "🎓 كلية تكنولوجيا المعلومات\n"
        "💻 قسم تكنولوجيا المعلومات (IT) - موازي\n\n"
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
    bot.send_message(chat_id, "📚 اختر المادة الدراسية:", reply_markup=make_keyboard(buttons))

def show_categories(chat_id, purpose):
    user_states[chat_id] = purpose
    bot.send_message(chat_id, "📂 اختر القسم المطلوب:", reply_markup=make_keyboard(CATEGORIES + ["⬅️ رجوع للمواد"]))

def is_admin(message):
    return message.from_user.id == ADMIN_ID

# ==========================================
# 5. أوامر وبداية البوت
# ==========================================
@bot.message_handler(commands=["start"])
def start(message):
    send_home(message.chat.id)

@bot.message_handler(func=lambda m: m.text is not None and m.text.strip().lower() == "admin")
def admin_panel(message):
    if not is_admin(message):
        bot.send_message(message.chat.id, "⛔ ليس لديك صلاحية دخول لوحة الإدارة.")
        return

    user_states[message.chat.id] = "admin_menu"
    bot.send_message(
        message.chat.id,
        "🔐 لوحة إدارة مكتبة الكلية\n\nاختر العملية المطلوبة:",
        reply_markup=make_keyboard([
            "➕ إضافة محتوى",
            "➕ إضافة مادة",
            "📋 عرض المحتوى",
            "🗑 حذف محتوى",
            "💬 أسئلة الطلاب",
            "🏠 القائمة الرئيسية"
        ])
    )

def begin_add_content(chat_id):
    user_data[chat_id] = {}
    send_semesters(chat_id, "admin_choose_semester")

def ask_next_content_field(chat_id, field):
    prompts = {
        "doctor": "👨‍🏫 اكتب اسم الدكتور:\nإذا لم يوجد، اكتب: لا يوجد",
        "subject": "📚 اكتب اسم المادة الدراسية:",
        "title": "📝 اكتب عنوان المحتوى أو المحاضرة:",
        "notes": "📌 اكتب ملاحظاتك:\nإذا لم يوجد، اكتب: لا يوجد",
        "payload": "📎 أرسل المحتوى الآن (ملف PDF، فيديو، صورة، نص، أو أي مرفق)."
    }
    user_states[chat_id] = "add_" + field
    bot.send_message(chat_id, prompts[field])

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
        "✅ تم إدراج المحتوى بنجاح!\n\n"
        f"📚 المادة: {data['subject']}\n"
        f"📂 القسم: {data['category']}\n"
        f"📝 العنوان: {data['title']}"
    )
    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)

@bot.message_handler(
    content_types=["text", "document", "video", "photo", "audio", "voice", "animation", "video_note"],
    func=lambda m: m.chat.id in user_states and user_states[m.chat.id] == "add_payload"
)
def receive_content(message):
    if not is_admin(message):
        return

    if message.content_type == "text":
        save_content(message.chat.id, "text", text_content=message.text)
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

    save_content(message.chat.id, message.content_type, file_id=file_id)

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
            conn.execute("INSERT INTO subjects (name, semester, system) VALUES (?, ?, ?)", (name, semester, SYSTEM))
        bot.send_message(chat_id, f"✅ تمت إضافة مادة {name} إلى {semester}.")
    except sqlite3.IntegrityError:
        bot.send_message(chat_id, "هذه المادة موجودة بالفعل في هذا الفصل.")

    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)

def list_content(chat_id):
    with connect_db() as conn:
        rows = conn.execute("SELECT id, subject, category, title FROM content ORDER BY id DESC LIMIT 30").fetchall()
    if not rows:
        bot.send_message(chat_id, "لا يوجد محتوى محفوظ.")
        return
    for row in rows:
        bot.send_message(chat_id, f"رقم المحتوى: {row['id']}\nالمادة: {row['subject']}\nالقسم: {row['category']}\nالعنوان: {row['title']}")

def delete_content_by_id(message):
    if not is_admin(message):
        return
    value = (message.text or "").strip()
    if not value.isdigit():
        bot.send_message(message.chat.id, "أرسل رقم المحتوى الذي تريد حذفه.")
        return
    with connect_db() as conn:
        cursor = conn.execute("DELETE FROM content WHERE id = ?", (int(value),))
    if cursor.rowcount:
        bot.send_message(message.chat.id, "✅ تم حذف المحتوى.")
    else:
        bot.send_message(message.chat.id, "لم يتم العثور على المحتوى.")
    user_states.pop(message.chat.id, None)

def save_question(message):
    chat_id = message.chat.id
    question = message.text or ""
    with connect_db() as conn:
        cursor = conn.execute("INSERT INTO questions (user_id, username, question) VALUES (?, ?, ?)", (message.from_user.id, message.from_user.username or "", question))
        question_id = cursor.lastrowid
    bot.send_message(chat_id, f"✅ تم إرسال سؤالك.\nرقم السؤال: {question_id}\nيمكنك متابعة حالته من زر «متابعة السؤال».")
    bot.send_message(ADMIN_ID, f"❓ سؤال جديد رقم {question_id}\nمن المستخدم: {message.from_user.id}\nاسم المستخدم: @{message.from_user.username or 'غير محدد'}\n\n{question}\n\nللرد اكتب:\nرد {question_id} ثم مسافة ثم نص الإجابة.")
    user_states.pop(chat_id, None)

def show_my_questions(message):
    with connect_db() as conn:
        rows = conn.execute("SELECT id, question, answer, status FROM questions WHERE user_id = ? ORDER BY id DESC LIMIT 15", (message.from_user.id,)).fetchall()
    if not rows:
        bot.send_message(message.chat.id, "ليس لديك أسئلة مسجلة حتى الآن.")
        return
    for row in rows:
        text = f"❓ السؤال رقم {row['id']}\n{row['question']}\n\nالحالة: {row['status']}"
        if row["answer"]:
            text += f"\n\n💬 الإجابة:\n{row['answer']}"
        bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text is not None and m.text.startswith("رد "))
def admin_answer(message):
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        bot.reply_to(message, "الصيغة الصحيحة:\nرد رقم_السؤال نص_الإجابة")
        return
    question_id = int(parts[1])
    answer = parts[2]
    with connect_db() as conn:
        row = conn.execute("SELECT user_id FROM questions WHERE id = ?", (question_id,)).fetchone()
        if row is None:
            bot.reply_to(message, "لم أجد هذا السؤال.")
            return
        conn.execute("UPDATE questions SET answer = ?, status = ? WHERE id = ?", (answer, "تمت الإجابة", question_id))
    bot.send_message(row["user_id"], f"💬 تمت الإجابة عن سؤالك رقم {question_id}:\n\n{answer}")
    bot.reply_to(message, "✅ تم إرسال الإجابة للطالب.")

def show_saved_content_list(chat_id, semester, subject, category):
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT * FROM content
            WHERE semester = ? AND subject = ? AND category = ?
            ORDER BY id DESC
        """, (semester, subject, category)).fetchall()
    
    if not rows:
        bot.send_message(chat_id, f"📭 لا يوجد محتوى مضاف حالياً في قسم ({category}) للمادة ({subject}).")
        return

    for item in rows:
        text = f"📚 المادة: {item['subject']}\n📂 القسم: {item['category']}\n📝 العنوان: {item['title']}\n"
        if item["doctor"]:
            text += f"👨‍🏫 الدكتور: {item['doctor']}\n"
        if item["notes"]:
            text += f"📌 ملاحظات: {item['notes']}\n"

        ctype = item["content_type"]
        if ctype == "text":
            bot.send_message(chat_id, text + "\n" + item["text_content"])
        elif ctype == "document":
            bot.send_document(chat_id, item["file_id"], caption=text)
        elif ctype == "video":
            bot.send_video(chat_id, item["file_id"], caption=text)
        elif ctype == "photo":
            bot.send_photo(chat_id, item["file_id"], caption=text)
        elif ctype == "audio":
            bot.send_audio(chat_id, item["file_id"], caption=text)
        elif ctype == "voice":
            bot.send_voice(chat_id, item["file_id"])
            bot.send_message(chat_id, text)
        elif ctype == "animation":
            bot.send_animation(chat_id, item["file_id"], caption=text)
        elif ctype == "video_note":
            bot.send_video_note(chat_id, item["file_id"])
            bot.send_message(chat_id, text)
        else:
            bot.send_message(chat_id, text + "\n" + item["text_content"])

# ==========================================
# معالج الرسائل والقوائم التفاعلية
# ==========================================
@bot.message_handler(func=lambda m: m.text is not None and not m.text.startswith("/"))
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()
    if text.lower() == "admin":
        return

    # 1. القائمة الرئيسية السفلية للطلاب
    if text == "📚 المواد الدراسية":
        send_semesters(chat_id, "student_semester")
        return
    elif text == "📎 الملحقات":
        send_semesters(chat_id, "student_attachments_semester")
        return
    elif text == "📅 الجدول الدراسي":
        send_semesters(chat_id, "student_schedule_semester")
        return
    elif text == "🔔 التذكيرات":
        send_semesters(chat_id, "student_reminders_semester")
        return
    elif text == "❓ طرح السؤال":
        user_states[chat_id] = "ask_question"
        bot.send_message(chat_id, "اكتب سؤالك الآن وسيتم إرساله إلى إدارة البوت:")
        return
    elif text == "💬 متابعة السؤال":
        show_my_questions(message)
        return
    elif text == "👨‍💻 مطور البوت":
        bot.send_message(
            chat_id,
            "👨‍💻 **مطور البوت:**\n"
            "المهندس / محمد الظاهر\n\n"
            "مخصص لخدمة طلاب كلية تكنولوجيا المعلومات - قسم (IT) موازي بجامعة إقليم سبأ."
        )
        return

    state = user_states.get(chat_id)

    # 2. خطوات إضافة المحتوى للأدمن
    if state == "add_doctor":
        user_data[chat_id]["doctor"] = "" if text == "لا يوجد" else text
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
        user_data[chat_id]["notes"] = "" if text == "لا يوجد" else text
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
            bot.send_message(chat_id, "أرسل رقم المحتوى الذي تريد حذفه:")
        elif text == "💬 أسئلة الطلاب":
            with connect_db() as conn:
                rows = conn.execute("SELECT id, user_id, question, status FROM questions ORDER BY id DESC LIMIT 20").fetchall()
            if not rows:
                bot.send_message(chat_id, "لا توجد أسئلة حالياً.")
            else:
                for row in rows:
                    bot.send_message(chat_id, f"السؤال رقم: {row['id']}\nالطالب: {row['user_id']}\nالحالة: {row['status']}\n\n{row['question']}\n\nللرد:\nرد {row['id']} نص الإجابة")
        elif text == "🏠 القائمة الرئيسية":
            send_home(chat_id)
        return

    # 3. اختيار الفصل الدراسي
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
        if text not in ("الفصل الدراسي الأول", "الفصل الدراسي الثاني"):
            bot.send_message(chat_id, "الرجاء اختيار أحد الفصلين من القائمة المتاحة.")
            return

        user_data.setdefault(chat_id, {})
        user_data[chat_id]["semester"] = text

        if state == "admin_choose_semester":
            user_states[chat_id] = "add_doctor"
            ask_next_content_field(chat_id, "doctor")
        elif state == "admin_new_subject_semester":
            user_states[chat_id] = "new_subject_name"
            bot.send_message(chat_id, "اكتب اسم المادة الدراسية الجديدة:")
        elif state == "student_semester":
            user_states[chat_id] = "student_choose_subject"
            show_subjects(chat_id, text, "student_choose_subject")
        return

    # 4. تصفح المواد والأقسام للطالب
    if state == "student_choose_subject":
        if text == "⬅️ رجوع للقائمة":
            send_home(chat_id)
            return
        user_data[chat_id]["subject"] = text
        show_categories(chat_id, "student_choose_category")
        return

    if state == "student_choose_category":
        if text == "⬅️ رجوع للمواد":
            semester = user_data.get(chat_id, {}).get("semester", "الفصل الدراسي الأول")
            show_subjects(chat_id, semester, "student_cho