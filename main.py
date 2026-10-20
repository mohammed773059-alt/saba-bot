import os
import sqlite3
import threading
import logging
import telebot
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running online!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_USER_ID", "0")

if not TOKEN:
    raise RuntimeError("يجب إعداد TELEGRAM_BOT_TOKEN في المتغيرات.")

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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reminder TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

init_db()

def make_reply_keyboard(items, columns=2):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=columns)
    for i in range(0, len(items), columns):
        markup.row(*[KeyboardButton(x) for x in items[i:i + columns]])
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
    for idx, sub in enumerate(SUBJECTS):
        icon = icons[idx] if idx < len(icons) else "📚 "
        markup.add(InlineKeyboardButton(icon + sub, callback_data=f"{prefix}_{idx}"))
    markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
    return markup

def get_categories_inline(prefix="cat"):
    markup = InlineKeyboardMarkup()
    icons = {"المحاضرات": "📖 ", "شروحات فيديو": "🎥 ", "التكاليف": "📝 ", "ملفات PDF": "📄 ", "الملحقات": "📎 "}
    for cat in CATEGORIES:
        markup.add(InlineKeyboardButton(icons.get(cat, "📂 ") + cat, callback_data=f"{prefix}_{cat}"))
    markup.add(InlineKeyboardButton("🔄 رجوع للمواد", callback_data="back_to_subjects"))
    markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
    return markup

def safe_edit(call, text, markup=None):
    try:
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

def show_content(chat_id, row):
    ctype, fid, tcont = row["content_type"], row["file_id"], row["text_content"]
    caption = f"📚 المادة: {row['subject']}\n📖 العنوان: {row['title']}\n📂 القسم: {row['category']}\n👨‍🏫 الدكتور: {row['doctor'] or 'غير محدد'}\n📌 الملاحظات: {row['notes'] or 'لا توجد'}"
    try:
        if ctype == "text":
            bot.send_message(chat_id, caption + "\n\n" + tcont)
        elif ctype == "photo":
            bot.send_photo(chat_id, fid, caption=caption)
        elif ctype == "document":
            bot.send_document(chat_id, fid, caption=caption)
        elif ctype == "video":
            bot.send_video(chat_id, fid, caption=caption)
        elif ctype == "audio":
            bot.send_audio(chat_id, fid, caption=caption)
        elif ctype == "voice":
            bot.send_voice(chat_id, fid)
        elif ctype == "animation":
            bot.send_animation(chat_id, fid, caption=caption)
        elif ctype == "video_note":
            bot.send_video_note(chat_id, fid)
    except Exception:
        bot.send_message(chat_id, "تعذر عرض هذا المحتوى.")

@bot.message_handler(commands=["start"])
def start(message):
    send_home(message.chat.id)

@bot.message_handler(commands=["admin"])
@bot.message_handler(func=lambda m: m.text in ["admin", "ادمن", "⚙️ لوحة الإدارة"])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ ليس لديك صلاحية.")
        return
    user_states[message.chat.id] = "admin_menu"
    bot.send_message(message.chat.id, "🔐 لوحة الإدارة:", reply_markup=make_reply_keyboard(ADMIN_MENU_ITEMS))

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data
    try:
        if data == "go_home":
            send_home(chat_id)
            bot.answer_callback_query(call.id)
            return

        if data.startswith("admin_sub_"):
            idx = int(data.split("_")[2])
            user_data.setdefault(chat_id, {})["subject"] = SUBJECTS[idx]
            safe_edit(call, f"➕ المادة: {SUBJECTS[idx]}\nاختر القسم:", get_categories_inline("admin_cat"))
            bot.answer_callback_query(call.id)
            return

        if data.startswith("admin_cat_"):
            cat = data.replace("admin_cat_", "", 1)
            user_data.setdefault(chat_id, {})["category"] = cat
            bot.send_message(chat_id, f"📚 المادة: {user_data[chat_id]['subject']}\n📂 القسم: {cat}")
            user_states[chat_id] = "admin_add_doctor"
            bot.send_message(chat_id, "👨‍🏫 اكتب اسم الدكتور، أو أرسل: لا يوجد")
            bot.answer_callback_query(call.id)
            return

        if data.startswith("sub_") or data.startswith("submat_"):
            is_att = data.startswith("submat_")
            idx = int(data.split("_")[1])
            sub = SUBJECTS[idx]
            user_data.setdefault(chat_id, {})["subject"] = sub
            
            if is_att:
                with connect_db() as conn:
                    rows = conn.execute("SELECT DISTINCT title FROM content WHERE subject = ? AND category = 'الملحقات' ORDER BY id", (sub,)).fetchall()
                markup = InlineKeyboardMarkup()
                if not rows:
                    markup.add(InlineKeyboardButton("🔄 رجوع", callback_data="back_to_attachments_subjects"), InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                    safe_edit(call, f"📎 ملحقات مادة: {sub}\n\n⏳ لا توجد ملحقات مدرجة لهذه المادة حالياً.", markup)
                else:
                    for r in rows:
                        markup.add(InlineKeyboardButton(f"📖 {r['title']}", callback_data=f"attlec_{r['title']}"))
                    markup.add(InlineKeyboardButton("🔄 رجوع", callback_data="back_to_attachments_subjects"), InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                    safe_edit(call, f"📎 ملحقات مادة: {sub}\nاختر المحاضرة:", markup)
            else:
                safe_edit(call, f"📚 {sub}\nاختر القسم:", get_categories_inline("cat"))
            bot.answer_callback_query(call.id)
            return

        if data == "back_to_subjects":
            safe_edit(call, "📚 اختر المادة التعليمية:", get_subjects_inline("sub"))
            bot.answer_callback_query(call.id)
            return

        if data == "back_to_attachments_subjects":
            markup = InlineKeyboardMarkup()
            for idx, sub in enumerate(SUBJECTS):
                icons = ["📖 ", "📖 ", "📐 ", "⚛️ ", "💻 ", "💻 "]
                icon = icons[idx] if idx < len(icons) else "📚 "
                markup.add(InlineKeyboardButton(icon + sub, callback_data=f"submat_{idx}"))
            markup.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
            safe_edit(call, "📎 اختر المادة لعرض ملحقاتها المرتبطة:", markup)
            bot.answer_callback_query(call.id)
            return

        if data.startswith("cat_"):
            cat = data.replace("cat_", "", 1)
            sub = user_data.get(chat_id, {}).get("subject", "عام")
            
            if cat == "الملحقات":
                with connect_db() as conn:
                    rows = conn.execute("SELECT DISTINCT title FROM content WHERE subject = ? AND category = 'الملحقات' ORDER BY id", (sub,)).fetchall()
                markup = InlineKeyboardMarkup()
                if not rows:
                    markup.add(InlineKeyboardButton("🔄 رجوع للأقسام", callback_data="back_to_cats"), InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                    safe_edit(call, f"📎 ملحقات مادة: {sub}\n\n⏳ لا توجد ملحقات مدرجة.", markup)
                else:
                    for r in rows:
                        markup.add(InlineKeyboardButton(f"📖 {r['title']}", callback_data=f"attlec_{r['title']}"))
                    markup.add(InlineKeyboardButton("🔄 رجوع للأقسام", callback_data="back_to_cats"), InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                    safe_edit(call, f"📎 ملحقات مادة: {sub}\nاختر المحاضرة:", markup)
                bot.answer_callback_query(call.id)
                return

            with connect_db() as conn:
                rows = conn.execute("SELECT DISTINCT title FROM content WHERE subject = ? AND category = ? ORDER BY id", (sub, cat)).fetchall()
            markup = InlineKeyboardMarkup()
            if not rows:
                markup.add(InlineKeyboardButton("🔄 رجوع", callback_data="back_to_cats"), InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                safe_edit(call, f"📂 {cat} - {sub}\n\n⏳ لا توجد محتويات.", markup)
            else:
                for r in rows:
                    markup.add(InlineKeyboardButton(f"📖 {r['title']}", callback_data=f"lec_{r['title']}"))
                markup.add(InlineKeyboardButton("🔄 رجوع", callback_data="back_to_cats"), InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                safe_edit(call, f"📚 {sub} ➔ {cat}\nاختر المحاضرة:", markup)
            bot.answer_callback_query(call.id)
            return

        if data == "back_to_cats":
            sub = user_data.get(chat_id, {}).get("subject", "عام")
            safe_edit(call, f"📚 {sub}\nاختر القسم:", get_categories_inline("cat"))
            bot.answer_callback_query(call.id)
            return

        if data.startswith("lec_"):
            lec = data.replace("lec_", "", 1)
            sub = user_data.get(chat_id, {}).get("subject", "عام")
            user_data.setdefault(chat_id, {})["current_lecture"] = lec
            with connect_db() as conn:
                rows = conn.execute("SELECT DISTINCT category FROM content WHERE subject = ? AND title = ?", (sub, lec)).fetchall()
            avail = [r["category"] for r in rows]
            markup = InlineKeyboardMarkup()
            c_btns = {"المحاضرات": "📄 ملف المحاضرة", "شروحات فيديو": "🎥 فيديو الشرح", "التكاليف": "📝 التكليف", "ملفات PDF": "📄 ملفات PDF", "الملحقات": "📎 الملحقات"}
            for c in CATEGORIES:
                if c in avail:
                    markup.add(InlineKeyboardButton(c_btns.get(c, c), callback_data=f"showcontent_{c}"))
            markup.add(InlineKeyboardButton("🔄 رجوع", callback_data="back_to_cats"), InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
            safe_edit(call, f"📖 المحاضرة: {lec}\n📚 المادة: {sub}\n\nاختر نوع المحتوى:", markup)
            bot.answer_callback_query(call.id)
            return

        if data.startswith("attlec_") or data.startswith("showcontent_"):
            is_att = data.startswith("attlec_")
            target = data.replace("attlec_" if is_att else "showcontent_", "", 1)
            sub = user_data.get(chat_id, {}).get("subject", "عام")
            lec = user_data.get(chat_id, {}).get("current_lecture", "")
            cat = "الملحقات" if is_att else target
            
            with connect_db() as conn:
                q_sql = "SELECT * FROM content WHERE subject = ? AND title = ? AND category = ? ORDER BY id"
                rows = conn.execute(q_sql, (sub, lec, cat) if not is_att else (sub, target, "الملحقات")).fetchall()
            
            if not rows:
                bot.answer_callback_query(call.id, "لا توجد محتويات.", show_alert=True)
                return
            for r in rows:
                show_content(chat_id, r)
            bot.answer_callback_query(call.id)
            return
    except Exception:
        logger.exception("Callback error")

@bot.message_handler(content_types=["text", "document", "video", "photo", "audio", "voice", "animation", "video_note"])
def handle_all_messages(message):
    chat_id = message.chat.id
    text = message.text.strip() if message.text else ""
    state = user_states.get(chat_id)

    if state == "ask_question":
        with connect_db() as conn:
            cur = conn.execute("INSERT INTO questions (user_id, username, question) VALUES (?, ?, ?)", (message.from_user.id, message.from_user.username or "بدون", text))
            qid = cur.lastrowid
        bot.send_message(chat_id, f"✅ تم إرسال سؤالك برقم: {qid}", reply_markup=make_reply_keyboard(HOME_ITEMS))
        
        if ADMIN_ID != 0:
            try:
                bot.send_message(
                    ADMIN_ID,
                    f"❓ سؤال جديد رقم: {qid}\n"
                    f"👤 من الطالب: {message.from_user.first_name} (@{message.from_user.username or 'بدون'})\n"
                    f"🆔 معرف الطالب: `{message.from_user.id}`\n\n"
                    f"💬 نص السؤال:\n{text}\n\n"
                    f"👇 للرد أرسل:\n`رد {qid} نص الإجابة`",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        user_states.pop(chat_id, None)
        return

    if state == "admin_upload_schedule":
        with connect_db() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, content_type, file_id, text_content) VALUES ('schedule', ?, ?, ?)", 
                         (message.content_type, message.photo[-1].file_id if message.content_type == "photo" else (message.document.file_id if message.content_type == "document" else (message.video.file_id if message.content_type == "video" else "")), text))
        bot.send_message(chat_id, "✅ تم رفع وتحديث الجدول الدراسي بنجاح.", reply_markup=make_reply_keyboard(ADMIN_MENU_ITEMS))
        user_states.pop(chat_id, None)
        return

    if state and state.startswith("admin_add_"):
        d = user_data.setdefault(chat_id, {})
        if state == "admin_add_doctor":
            d["doctor"] = "" if text == "لا يوجد" else text
            user_states[chat_id] = "admin_add_title"
            bot.send_message(chat_id, "📝 اكتب عنوان المحاضرة (مثال: المحاضرة الأولى):")
            return
        elif state == "admin_add_title":
            d["title"] = text
            user_states[chat_id] = "admin_add_notes"
            bot.send_message(chat_id, "📌 اكتب ملاحظات (أو أرسل: لا يوجد):")
            return
        elif state == "admin_add_notes":
            d["notes"] = "" if text == "لا يوجد" else text
            user_states[chat_id] = "admin_add_payload"
            bot.send_message(chat_id, "📎 أرسل الملف أو المحتوى الآن:")
            return
        elif state == "admin_add_payload":
            ctype = message.content_type
            fid = message.photo[-1].file_id if ctype == "photo" else (message.document.file_id if ctype == "document" else (message.video.file_id if ctype == "video" else ""))
            with connect_db() as conn:
                conn.execute("INSERT INTO content (subject, category, doctor, title, notes, content_type, file_id, text_content) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (d.get("subject"), d.get("category"), d.get("doctor"), d.get("title"), d.get("notes"), ctype, fid, text if ctype == "text" else ""))
            bot.send_message(chat_id, "✅ تمت الإضافة بنجاح!", reply_markup=make_reply_keyboard(ADMIN_AFTER_SAVE_ITEMS))
            user_states.pop(chat_id, None)
            user_data.pop(chat_id, None)
            return

    if text.startswith("رد ") and is_admin(message.from_user.id):
        parts = text.split(maxsplit=2)
        if len(parts) >= 3 and parts[1].isdigit():
            qid, ans = int(parts[1]), parts[2]
            with connect_db() as conn:
                row = conn.execute("SELECT user_id, question FROM questions WHERE id = ?", (qid,)).fetchone()
                if row:
                    conn.execute("UPDATE questions SET answer = ?, status = 'تمت الإجابة' WHERE id = ?", (ans, qid))
                    try:
                        bot.send_message(row["user_id"], f"🔔 تمت الإجابة على سؤالك رقم ({qid}):\n\n❓ السؤال: {row['question']}\n\n💬 الإجابة:\n{ans}")
                    except Exception:
                        pass
                    bot.reply_to(message, "✅ تم إرسال الإجابة إلى الطالب بنجاح.")
        return

    if text in ["📚 المواد التعليمية", "📚 المواد الدراسية"]:
        bot.send_message(chat_id, "📚 اختر المادة التعليمية:", reply_markup=get_subjects_inline("sub"))
    elif text == "📎 الملحقات":
        markup = InlineKeyboardMarkup()
        for idx, sub in enumerate(SUBJECTS):
            icons = ["📖 ", "📖 ", "📐 ", "⚛️ ", "💻 ", "💻 "]
            icon = icons[idx] if idx < len(icons) else "📚 "
            markup.add(InlineKeyboardButton(icon + sub, callback_data=f"submat_{idx}"))
        markup.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
        bot.send_message(chat_id, "📎 قسم الملحقات الدراسية:\nاختر المادة لعرض ملحقاتها المرتبطة:", reply_markup=markup)
    elif text == "📅 الجدول الدراسي":
        with connect_db() as conn:
            sched = conn.execute("SELECT * FROM settings WHERE key = 'schedule'").fetchone()
        if not sched:
            bot.send_message(chat_id, "📅 الجدول الدراسي غير متوفر حالياً.\n⏳ سوف يتم إدراجه قريباً من قبل إدارة البوت.")
        