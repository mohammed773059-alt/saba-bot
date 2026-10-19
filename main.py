import os
import sqlite3
import threading
import telebot
from flask import Flask

# ==========================================
# إعدادات البوت وقاعدة البيانات
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

init_db()

def make_reply_keyboard(items, columns=2):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=columns)
    for i in range(0, len(items), columns):
        markup.row(*[telebot.types.KeyboardButton(x) for x in items[i:i + columns]])
    return markup

def send_home(chat_id):
    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)
    try:
        bot.send_message(
            chat_id,
            "🎓 **كلية تكنولوجيا المعلومات**\n"
            "💻 **قسم تكنولوجيا المعلومات (IT) - موازي**\n\n"
            "اختر الخدمة التي تريدها:",
            reply_markup=make_reply_keyboard(HOME_ITEMS),
            parse_mode="Markdown"
        )
    except Exception:
        pass

def is_admin(user_id):
    return ADMIN_ID == 0 or user_id == ADMIN_ID

def get_subjects_inline(prefix="sub"):
    markup = telebot.types.InlineKeyboardMarkup()
    icons = ["📖 ", "📖 ", "📐 ", "⚛️ ", "💻 ", "💻 "]
    for idx, sub in enumerate(SUBJECTS):
        icon = icons[idx] if idx < len(icons) else "📚 "
        markup.add(telebot.types.InlineKeyboardButton(f"{icon}{sub}", callback_data=f"{prefix}_{idx}"))
    markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
    return markup

def get_categories_inline(prefix="cat"):
    markup = telebot.types.InlineKeyboardMarkup()
    cat_icons = {
        "المحاضرات": "📖 ",
        "شروحات فيديو": "🎥 ",
        "التكاليف": "📝 ",
        "ملفات PDF": "📄 ",
        "الملحقات": "📎 "
    }
    for cat in CATEGORIES:
        icon = cat_icons.get(cat, "📂 ")
        markup.add(telebot.types.InlineKeyboardButton(f"{icon}{cat}", callback_data=f"{prefix}_{cat}"))
    markup.add(telebot.types.InlineKeyboardButton("🔄 رجوع للمواد", callback_data="back_to_subjects"))
    markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    send_home(message.chat.id)

@bot.message_handler(commands=["admin"])
@bot.message_handler(func=lambda m: m.text is not None and m.text.strip().lower() in ["admin", "ادمن", "⚙️ لوحة الإدارة"])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ ليس لديك صلاحية دخول لوحة الإدارة.")
        return

    user_states[message.chat.id] = "admin_menu"
    bot.send_message(
        message.chat.id,
        "🔐 **لوحة إدارة مكتبة الكلية**\n\nاختر العملية المطلوبة:",
        reply_markup=make_reply_keyboard(ADMIN_MENU_ITEMS)
    )

def ask_admin_field(chat_id, field):
    prompts = {
        "doctor": "👨‍🏫 **اكتب اسم الدكتور:**\n(إذا لم يوجد، أرسل: لا يوجد)",
        "title": "📝 **اكتب اسم المحاضرة التي سيندرج تحتها المحتوى:**\n(مثال: المحاضرة الأولى، المحاضرة الثانية...)",
        "notes": "📌 **اكتب الملاحظات:**\n(إذا لم يوجد، أرسل: لا يوجد)",
        "payload": "📎 **أرسل المحتوى الآن:**\n(ملف PDF، فيديو، صورة، رابط، نص، أو تسجيل صوتي)"
    }
    user_states[chat_id] = "admin_add_" + field
    bot.send_message(chat_id, prompts[field], parse_mode="Markdown")

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
        f"📂 **القسم:** {data.get('category')}\n"
        f"👨‍🏫 **الدكتور:** {data.get('doctor') or 'غير محدد'}\n\n"
        "ماذا تريد أن تفعل الآن؟",
        reply_markup=make_reply_keyboard(ADMIN_AFTER_SAVE_ITEMS),
        parse_mode="Markdown"
    )
    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)

def save_user_question(message):
    chat_id = message.chat.id
    q_text = message.text or ""

    with connect_db() as conn:
        cursor = conn.execute("""
            INSERT INTO questions (user_id, username, question)
            VALUES (?, ?, ?)
        """, (message.from_user.id, message.from_user.username or "بدون معرف", q_text))
        q_id = cursor.lastrowid

    bot.send_message(
        chat_id,
        f"✅ **تم إرسال سؤالك بنجاح!**\n\n"
        f"🔢 **رقم السؤال:** `{q_id}`\n"
        f"سيتم مراجعته والإجابة عليه قريباً. يمكنك الضغط على «💬 متابعة السؤال» لمعرفة الإجابة لاحقاً.",
        reply_markup=make_reply_keyboard(HOME_ITEMS),
        parse_mode="Markdown"
    )

    if ADMIN_ID != 0:
        try:
            bot.send_message(
                ADMIN_ID,
                f"❓ **سؤال جديد رقم:** `{q_id}`\n"
                f"👤 **من الطالب:** {message.from_user.first_name} (@{message.from_user.username or 'بدون'})\n"
                f"🆔 **معرف الطالب:** `{message.from_user.id}`\n\n"
                f"💬 **نص السؤال:**\n{q_text}\n\n"
                f"👇 **للرد على السؤال، أرسل الرسالة التالية:**\n`رد {q_id} نص الإجابة هنا`",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    user_states.pop(chat_id, None)

def show_user_questions(message):
    chat_id = message.chat.id
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT id, question, answer, status, created_at FROM questions
            WHERE user_id = ? ORDER BY id DESC LIMIT 10
        """, (message.from_user.id,)).fetchall()

    if not rows:
        bot.send_message(chat_id, "ℹ️ ليس لديك أسئلة مسجلة حالياً.")
        return

    for row in rows:
        msg = f"❓ **السؤال رقم:** `{row['id']}`\n"
        msg += f"📝 **سؤالك:** {row['question']}\n"
        msg += f"📌 **الحالة:** {row['status']}\n"
        if row["answer"]:
            msg += f"\n💬 **الإجابة:**\n{row['answer']}"
        bot.send_message(chat_id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text is not None and m.text.startswith("رد "))
def reply_to_question(message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        bot.reply_to(message, "⚠️ **صيغة الرد الخاطئة!**\nالصيغة الصحيحة:\n`رد رقم_السؤال نص الإجابة`", parse_mode="Markdown")
        return

    q_id = int(parts[1])
    ans_text = parts[2]

    with connect_db() as conn:
        q_row = conn.execute("SELECT user_id, question FROM questions WHERE id = ?", (q_id,)).fetchone()
        if not q_row:
            bot.reply_to(message, "❌ لم يتم العثور على سؤال بهذا الرقم.")
            return

        conn.execute("""
            UPDATE questions
            SET answer = ?, status = 'تمت الإجابة'
            WHERE id = ?
        """, (ans_text, q_id))

    try:
        bot.send_message(
            q_row["user_id"],
            f"🔔 **تمت الإجابة على سؤالك رقم ({q_id}):**\n\n"
            f"❓ **السؤال:** {q_row['question']}\n\n"
            f"💬 **الإجابة:**\n{ans_text}",
            parse_mode="Markdown"
        )
        bot.reply_to(message, "✅ تم إرسال الإجابة إلى الطالب بنجاح!")
    except Exception:
        bot.reply_to(message, "✅ تم حفظ الإجابة في قاعدة البيانات (تعذر مراسلة الطالب مباشرة).")

@bot.message_handler(
    content_types=["text", "document", "video", "photo", "audio", "voice", "animation", "video_note"],
    func=lambda m: user_states.get(m.chat.id) in ["admin_add_payload", "admin_upload_schedule"]
)
def receive_payload(message):
    if not is_admin(message.from_user.id):
        return

    chat_id = message.chat.id
    state = user_states.get(chat_id)

    if state == "admin_upload_schedule":
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

        with connect_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO settings (key, content_type, file_id, text_content)
                VALUES ('schedule', ?, ?, ?)
            """, (content_type, file_id, text_content))

        bot.send_message(
            chat_id,
            "✅ **تم تحديث ورفع الجدول الدراسي بنجاح!**",
            reply_markup=make_reply_keyboard(ADMIN_MENU_ITEMS),
            parse_mode="Markdown"
        )
        user_states.pop(chat_id, None)
        return

    if message.content_type == "text":
        save_content_db(chat_id, "text", text_content=message.text)
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

    save_content_db(chat_id, message.content_type, file_id=file_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "go_home":
        send_home(chat_id)
        bot.answer_callback_query(call.id)
        return

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

    if data.startswith("sub_") or data.startswith("submat_"):
        is_attachment_mode = data.startswith("submat_")
        sub_idx = int(data.split("_")[1])
        subject_name = SUBJECTS[sub_idx]
        user_data.setdefault(chat_id, {})["subject"] = subject_name
        user_data[chat_id]["mode"] = "attachments" if is_attachment_mode else "normal"

        if is_attachment_mode:
            with connect_db() as conn:
                rows = conn.execute("""
                    SELECT DISTINCT title FROM content
                    WHERE subject = ?
                    ORDER BY id ASC
                """, (subject_name,)).fetchall()

            if not rows:
                back_markup = telebot.types.InlineKeyboardMarkup()
                back_markup.add(telebot.types.InlineKeyboardButton("🔄 رجوع للمواد", callback_data="back_to_attachments_subjects"))
                back_markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
                bot.edit_message_text(
                    f"📎 **ملحقات مادة:** {subject_name}\n\n⏳ **سوف يتم إدراج المحتويات قريباً.**",
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    reply_markup=back_markup
                )
                bot.answer_callback_query(call.id)
                return

            markup = telebot.types.InlineKeyboardMarkup()
            for row in rows:
                markup.add(telebot.types.InlineKeyboardButton(f"📖 {row['title']}", callback_data=f"attlec_{row['title']}"))
            markup.add(telebot.types.InlineKeyboardButton("🔄 رجوع للمواد", callback_data="back_to_attachments_subjects"))
            markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))

            bot.edit_message_text(
                f"📎 **ملحقات مادة:** {subject_name}\nاختر المحاضرة المطلوبة:",
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        else:
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

    if data == "back_to_attachments_subjects":
        markup = telebot.types.InlineKeyboardMarkup()
        icons = ["📖 ", "📖 ", "📐 ", "⚛️ ", "💻 ", "💻 "]
        for idx, sub in enumerate(SUBJECTS):
            icon = icons[idx] if idx < len(icons) else "📚 "
            markup.add(telebot.types.InlineKeyboardButton(f"{icon}{sub}", callback_data=f"submat_{idx}"))
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
        bot.edit_message_text(
            "📎 **اختر المادة لعرض ملحقاتها المرتبطة:**",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
        return

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
            back_cats_markup = telebot.types.InlineKeyboardMarkup()
            back_cats_markup.add(telebot.types.InlineKeyboardButton("🔄 رجوع للأقسام", callback_data="back_to_cats"))
            back_cats_markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
            
            bot.edit_message_text(
                f"📂 **{category_name}** - {subject}\n\n⏳ **سوف يتم إدراج المحاضرات والمحتويات قريباً.**",
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=back_cats_markup
            )
            bot.answer_callback_query(call.id)
            return

        markup = telebot.types.InlineKeyboardMarkup()
        for row in rows:
            markup.add(telebot.types.InlineKeyboardButton(f"📖 {row['title']}", callback_data=f"lec_{row['title']}"))
        
        markup.add(telebot.types.InlineKeyboardButton("🔄 رجوع للأقسام", callback_data="back_to_cats"))
        markup.add(telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))

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

        markup = telebot.types.InlineKeyboardMarkup()
        cat_icons = {
            "المحاضرات": "📄 ملف المحاضرة (PDF/نص)",
            "شروحات فيديو": "🎥 فيديو الشرح",
            "التكاليف": "📝 التكليف",
      