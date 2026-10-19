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
ADMIN_ID = os.getenv("ADMIN_USER_ID", "")

if not TOKEN:
    raise RuntimeError("يجب إعداد TELEGRAM_BOT_TOKEN في Secrets.")

if not ADMIN_ID.isdigit():
    raise RuntimeError("يجب إعداد ADMIN_USER_ID برقم حساب المدير.")

ADMIN_ID = int(ADMIN_ID)

bot = telebot.TeleBot(TOKEN)

DB_FILE = "library.db"
SYSTEM = "الموازي"

# المواد المعتمدة الـ 6
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
                semester TEXT NOT NULL DEFAULT 'الفصل الدراسي الأول',
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
        "🎓 كلية تكنولوجيا المعلومات\n"
        "💻 قسم تكنولوجيا المعلومات (IT) - موازي\n\n"
        "اختر الخدمة التي تريدها:",
        reply_markup=make_reply_keyboard(HOME_ITEMS)
    )

def is_admin(message):
    return message.from_user.id == ADMIN_ID

# أزرار المواد إنلاين للطلاب وللأدمن
def get_subjects_inline(action_prefix="sub"):
    markup = InlineKeyboardMarkup()
    icons = ["📖 ", "📖 ", "📐 ", "⚛️ ", "💻 ", "💻 "]
    for idx, sub in enumerate(SUBJECTS):
        icon = icons[idx] if idx < len(icons) else "📚 "
        markup.add(InlineKeyboardButton(f"{icon}{sub}", callback_data=f"{action_prefix}_{idx}"))
    markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
    return markup

# أزرار الأقسام إنلاين
def get_categories_inline(action_prefix="cat"):
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
        markup.add(InlineKeyboardButton(f"{icon}{cat}", callback_data=f"{action_prefix}_{cat}"))
    markup.add(InlineKeyboardButton("🔄 رجوع للمواد", callback_data="back_to_subjects"))
    markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
    return markup

# ==========================================
# 5. لوحة الإدارة والأوامر
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
        "🔐 **لوحة إدارة مكتبة الكلية**\n\nاختر العملية المطلوبة:",
        reply_markup=make_reply_keyboard([
            "➕ إضافة محتوى",
            "📋 عرض المحتوى",
            "💬 أسئلة الطلاب",
            "🏠 القائمة الرئيسية"
        ])
    )

def ask_next_admin_field(chat_id, field):
    prompts = {
        "doctor": "👨‍🏫 اكتب اسم الدكتور:\n(إذا لم يوجد، أرسل كلمة: لا يوجد)",
        "title": "📝 اكتب عنوان المحتوى أو المحاضرة:",
        "notes": "📌 اكتب ملاحظاتك:\n(إذا لم يوجد، أرسل كلمة: لا يوجد)",
        "payload": "📎 أرسل المحتوى الآن (يقبل البوت: ملفات PDF، فيديوهات، صور، روابط، نصوص، تسجيلات صوتية...)"
    }
    user_states[chat_id] = "admin_add_" + field
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
            data.get("semester", "الفصل الدراسي الأول"),
            data.get("subject", "عام"),
            data.get("category", "المحاضرات"),
            data.get("doctor", ""),
            data.get("title", "بدون عنوان"),
            data.get("notes", ""),
            content_type,
            file_id,
            text_content
        ))

    bot.send_message(
        chat_id,
        "✅ **تم حفظ وإدراج المحتوى بنجاح!**\n\n"
        f"📚 **المادة:** {data.get('subject')}\n"
        f"📂 **القسم:** {data.get('category')}\n"
        f"👨‍🏫 **الدكتور:** {data.get('doctor') or 'غير محدد'}\n"
        f"📝 **العنوان:** {data.get('title')}\n\n"
        "أصبح المحتوى متاحاً لجميع الطلاب في المكتبة الآن."
    )
    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)

@bot.message_handler(
    content_types=["text", "document", "video", "photo", "audio", "voice", "animation", "video_note"],
    func=lambda m: m.chat.id in user_states and user_states[m.chat.id] == "admin_add_payload"
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

# ==========================================
# 6. التفاعل مع الضغط على الأزرار المدمجة
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "go_home":
        send_home(chat_id)
        bot.answer_callback_query(call.id)
        return

    # --- تسلسل الإضافة للـ ADMIN ---
    if data.startswith("admin_sub_"):
        sub_idx = int(data.split("_")[2])
        subject_name = SUBJECTS[sub_idx]
        user_data.setdefault(chat_id, {})["subject"] = subject_name
        
        bot.edit_message_text(
            f"➕ **المادة المختارة:** {subject_name}\nاختر القسم الذي تريد الإضافة إليه:",
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
            f"🎯 **بدء إضافة محتوى جديد**\n"
            f"📚 المادة: {user_data[chat_id]['subject']}\n"
            f"📂 القسم: {category_name}\n\n"
            "سنقوم الآن بأخذ تفاصيل المحتوى."
        )
        ask_next_admin_field(chat_id, "doctor")
        bot.answer_callback_query(call.id)
        return

    # --- تصفح الطلاب للمكتبة ---
    if data.startswith("sub_"):
        sub_idx = int(data.split("_")[1])
        subject_name = SUBJECTS[sub_idx]
        user_data.setdefault(chat_id, {})["subject"] = subject_name
        
        bot.edit_message_text(
            f"📚 **{subject_name}**\nاختر القسم الدراسي المطلوب:",
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

    if data.startswith("cat_"):
        category_name = data.replace("cat_", "")
        user_data.setdefault(chat_id, {})["category"] = category_name
        
        semester = user_data[chat_id].get("semester", "الفصل الدراسي الأول")
        subject = user_data[chat_id].get("subject", "عام")

        bot.send_message(chat_id, f"📂 **{category_name}** - {subject}")
        
        with connect_db() as conn:
            rows = conn.execute("""
                SELECT * FROM content
                WHERE subject = ? AND category = ?
                ORDER BY id DESC
            """, (subject, category_name)).fetchall()

        if not rows:
            bot.send_message(chat_id, "⌛ سوف يتم إدراج المحاضرات والمحتويات قريباً.")
        else:
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

        bot.answer_callback_query(call.id)
        return

# ==========================================
# 7. معالج الرسائل العادية
# ==========================================
@bot.message_handler(func=lambda m: m.text is not None and not m.text.startswith("/"))
def handle_message(message):
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
        bot.send_message(chat_id, "📎 قسم الملحقات والتنصيبات:\nسوف يتم رفعه قريباً.")
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

    # استقبال إجابات أسئلة الأدمن متسلسلة
    if state == "admin_add_doctor":
        user_data[chat_id]["doctor"] = "" if text == "لا يوجد" else text
        ask_next_admin_field(chat_id, "title")
        return

    if state == "admin_add_title":
        user_data[chat_id]["title"] = text
        ask_next_admin_field(chat_id, "notes")
        return

    if state == "admin_add_notes":
        user_data[chat_id]["notes"] = "" if text == "لا يوجد" else text
        ask_next_admin_field(chat_id, "payload")
        return

    if state == "ask_question":
        save_question(message)
        return

    if state == "admin_menu":
        if not is_admin(message):
            return
        if text == "➕ إضافة محتوى":
            user_data[chat_id] = {}
            bot.send_message(
                chat_id,
                "📚 **اختر المادة التي تريد إضافة محتوى إليها:**",
                reply_markup=get_subjects_inline("admin_sub")
            )
        elif text == "📋 عرض المحتوى":
            bot.send_message(chat_id, "يمكنك استعراض المحتوى المضاف مباشرة عبر أزرار المواد من القائمة الرئيسية.")
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

def start_bot():
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()
    run_flask()