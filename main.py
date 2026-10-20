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

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_USER_ID", "0").strip() or "0")

bot = telebot.TeleBot(TOKEN) if TOKEN else None
DB_FILE = "library.db"

SEMESTERS = [
    "الفصل الدراسي الأول",
    "الفصل الدراسي الثاني",
    "الفصل الدراسي الثالث",
    "الفصل الدراسي الرابع"
]

CATEGORIES = ["المحاضرات", "شروحات فيديو", "التكاليف", "ملفات PDF", "الملحقات"]

HOME_ITEMS = [
    "📚 المواد التعليمية", "📎 الملحقات", "📅 الجدول الدراسي",
    "❓ طرح السؤال", "💬 متابعة السؤال", "🔔 التذكيرات",
    "🔄 تغيير الفصل الدراسي", "👨‍💻 مطور البوت"
]

ADMIN_ITEMS = ["➕ إضافة محتوى", "🗑️ حذف محتوى", "📚 إضافة مادة جديدة", "💬 أسئلة الطلاب", "🏠 القائمة الرئيسية"]

user_states = {}
user_data = {}

def db():
    c = sqlite3.connect(DB_FILE, timeout=30)
    c.row_factory = sqlite3.Row
    return c

with db() as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS content (id INTEGER PRIMARY KEY AUTOINCREMENT, semester TEXT, subject TEXT, category TEXT, doctor TEXT, title TEXT, notes TEXT, content_type TEXT, file_id TEXT, text_content TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, content_type TEXT, file_id TEXT, text_content TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, question TEXT, answer TEXT, status TEXT DEFAULT 'قيد المراجعة')")
    conn.execute("CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, reminder TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS custom_subjects (id INTEGER PRIMARY KEY AUTOINCREMENT, semester TEXT, name TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS user_preferences (user_id INTEGER PRIMARY KEY, semester TEXT)")

def get_user_semester(user_id):
    try:
        with db() as conn:
            row = conn.execute("SELECT semester FROM user_preferences WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                return row["semester"]
    except Exception:
        pass
    return None

def set_user_semester(user_id, semester):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO user_preferences (user_id, semester) VALUES (?, ?)", (user_id, semester))

def get_subjects_by_sem(semester):
    subs = []
    if semester == "الفصل الدراسي الأول":
        subs = [
            "مهارة اللغة العربية", "مهارة اللغة الإنجليزية",
            "التفاضل والتكامل", "الفيزياء العامة وحوسبة",
            "مقدمة في الحوسبة", "مهارات الحاسوب"
        ]
    try:
        with db() as conn:
            rows = conn.execute("SELECT name FROM custom_subjects WHERE semester = ?", (semester,)).fetchall()
            for r in rows:
                if r["name"] not in subs:
                    subs.append(r["name"])
    except Exception:
        pass
    return subs

def kb(items, cols=2):
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=cols)
    for i in range(0, len(items), cols):
        m.row(*[KeyboardButton(x) for x in items[i:i+cols]])
    return m

def send_home(chat_id):
    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)
    if bot:
        bot.send_message(
            chat_id,
            "🎓 كلية تكنولوجيا المعلومات\n💻 قسم تكنولوجيا المعلومات (IT) - موازي\n\nاختر الخدمة التي تريدها:",
            reply_markup=kb(HOME_ITEMS)
        )

def show_subjects_for_user(chat_id, user_id):
    sem = get_user_semester(user_id)
    if not sem:
        m = InlineKeyboardMarkup()
        for i, s in enumerate(SEMESTERS):
            m.add(InlineKeyboardButton(f"🎓 {s}", callback_data=f"setsem_{i}"))
        bot.send_message(chat_id, "👋 أهلاً بك! يرجى اختيار فصلك الدراسي (لمرة واحدة فقط):", reply_markup=m)
    else:
        subs = get_subjects_by_sem(sem)
        m = InlineKeyboardMarkup()
        if not subs:
            m.add(InlineKeyboardButton("🔄 تغيير الفصل الدراسي", callback_data="change_my_sem"), InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
            bot.send_message(chat_id, f"📚 {sem}\n\n⏳ لا توجد مواد دراسية مضافة في هذا الفصل حالياً.", reply_markup=m)
        else:
            sem_idx = SEMESTERS.index(sem) if sem in SEMESTERS else 0
            for i, s in enumerate(subs):
                m.add(InlineKeyboardButton(f"📖 {s}", callback_data=f"sub_{sem_idx}_{i}"))
            m.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="go_home"))
            bot.send_message(chat_id, f"📚 مواد ({sem}):\nاختر المادة التعليمية:", reply_markup=m)

if bot:
    @bot.message_handler(commands=["start"])
    def start(m):
        send_home(m.chat.id)

    @bot.message_handler(commands=["admin"])
    @bot.message_handler(func=lambda m: m.text and m.text.lower() in ["admin", "ادمن", "⚙️ لوحة الإدارة"])
    def handle_admin_access(m):
        if m.from_user.id == ADMIN_ID:
            user_states[m.chat.id] = "admin_menu"
            bot.send_message(m.chat.id, "🔐 لوحة الإدارة:", reply_markup=kb(ADMIN_ITEMS))
        else:
            bot.send_message(m.chat.id, "⚠️ **تنبيه:** هذه القائمة خاصة بإدارة البوت فقط، ولا يمكنك الوصول إليها.", parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda c: True)
    def cb(c):
        cid = c.message.chat.id
        uid = c.from_user.id
        data = c.data
        try:
            if data == "go_home":
                send_home(cid)
            elif data.startswith("setsem_"):
                sem_idx = int(data.split("_")[1])
                chosen_sem = SEMESTERS[sem_idx]
                set_user_semester(uid, chosen_sem)
                bot.answer_callback_query(c.id, f"✅ تم تحديد {chosen_sem} بنجاح!")
                show_subjects_for_user(cid, uid)
            elif data == "change_my_sem":
                m = InlineKeyboardMarkup()
                for i, s in enumerate(SEMESTERS):
                    m.add(InlineKeyboardButton(f"🎓 {s}", callback_data=f"setsem_{i}"))
                m.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                bot.edit_message_text("🔄 اختر الفصل الدراسي الجديد:", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
            elif data.startswith("admin_sem_"):
                sem_idx = int(data.split("_")[2])
                sem = SEMESTERS[sem_idx]
                user_data.setdefault(cid, {})["subject_semester"] = sem
                m = InlineKeyboardMarkup()
                subs = get_subjects_by_sem(sem)
                for i, s in enumerate(subs):
                    m.add(InlineKeyboardButton(s, callback_data=f"admin_sub_{sem_idx}_{i}"))
                m.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                bot.edit_message_text(f"➕ إضافة محتوى في ({sem})\nاختر المادة:", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
            elif data.startswith("admin_sub_"):
                parts = data.split("_")
                sem_idx = int(parts[2])
                sub_idx = int(parts[3])
                sem = SEMESTERS[sem_idx]
                subs = get_subjects_by_sem(sem)
                sub = subs[sub_idx]
                user_data.setdefault(cid, {})["semester"] = sem
                user_data.setdefault(cid, {})["subject"] = sub
                m = InlineKeyboardMarkup()
                for cat in CATEGORIES:
                    m.add(InlineKeyboardButton(cat, callback_data=f"admin_cat_{cat}"))
                m.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                bot.edit_message_text(f"➕ المادة: {sub} ({sem})\nاختر القسم:", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
            elif data.startswith("admin_cat_"):
                cat = data.replace("admin_cat_", "", 1)
                user_data.setdefault(cid, {})["category"] = cat
                user_states[cid] = "admin_add_doc"
                bot.send_message(cid, f"📚 الفصل: {user_data[cid]['semester']}\n📖 المادة: {user_data[cid]['subject']}\n📂 القسم: {cat}\n\n👨‍🏫 اكتب اسم الدكتور (أو أرسل: لا يوجد):")
            elif data.startswith("addsub_sem_"):
                sem_idx = int(data.split("_")[2])
                sem = SEMESTERS[sem_idx]
                user_data.setdefault(cid, {})["new_sub_sem"] = sem
                user_states[cid] = "admin_save_new_subject"
                bot.send_message(cid, f"📚 أرسل اسم المادة الجديدة التي تريد إضافتها إلى ({sem}):")
            elif data.startswith("delsub_"):
                idx = int(data.split("_")[1])
                sem = get_user_semester(uid) or SEMESTERS[0]
                subs = get_subjects_by_sem(sem)
                if idx < len(subs):
                    sub = subs[idx]
                    user_data.setdefault(cid, {})["del_subject"] = sub
                    m = InlineKeyboardMarkup()
                    for cat in CATEGORIES:
                        m.add(InlineKeyboardButton(cat, callback_data=f"delcat_{cat}"))
                    m.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                    bot.edit_message_text(f"🗑️ حذف محتوى من مادة: {sub}\nاختر القسم:", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
            elif data.startswith("delcat_"):
                cat = data.replace("delcat_", "", 1)
                sub = user_data.get(cid, {}).get("del_subject", "")
                with db() as conn:
                    rows = conn.execute("SELECT id, title FROM content WHERE subject = ? AND category = ?", (sub, cat)).fetchall()
                m = InlineKeyboardMarkup()
                if not rows:
                    m.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                    bot.edit_message_text(f"⏳ لا توجد محتويات في ({sub} ➔ {cat}) للحذف.", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
                else:
                    for r in rows:
                        m.add(InlineKeyboardButton(f"❌ حذف: {r['title']}", callback_data=f"delfinal_{r['id']}"))
                    m.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                    bot.edit_message_text(f"🗑️ اختر المحتوى المراد حذفه من ({sub} - {cat}):", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
            elif data.startswith("delfinal_"):
                item_id = int(data.split("_")[1])
                with db() as conn:
                    conn.execute("DELETE FROM content WHERE id = ?", (item_id,))
                bot.answer_callback_query(c.id, "✅ تم الحذف بنجاح!", show_alert=True)
                bot.edit_message_text("✅ تم حذف المحتوى المحدد بنجاح.", chat_id=cid, message_id=c.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home")))
            elif data.startswith("sub_") or data.startswith("submat_"):
                parts = data.split("_")
                is_att = data.startswith("submat_")
                sem_idx = int(parts[1])
                sub_idx = int(parts[2])
                sem = SEMESTERS[sem_idx]
                subs = get_subjects_by_sem(sem)
                sub = subs[sub_idx]
                user_data.setdefault(cid, {})["semester"] = sem
                user_data.setdefault(cid, {})["subject"] = sub
                m = InlineKeyboardMarkup()
                if is_att:
                    with db() as conn:
                        rows = conn.execute("SELECT DISTINCT title FROM content WHERE semester = ? AND subject = ? AND category = 'الملحقات'", (sem, sub)).fetchall()
                    if not rows:
                        m.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                        bot.edit_message_text(f"📎 ملحقات مادة: {sub}\n\n⏳ لا توجد ملحقات.", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
                    else:
                        for r in rows:
                            m.add(InlineKeyboardButton(f"📖 {r['title']}", callback_data=f"attlec_{r['title']}"))
                        m.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                        bot.edit_message_text(f"📎 ملحقات مادة: {sub}\nاختر المحاضرة:", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
                else:
                    for cat in CATEGORIES:
                        m.add(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
                    m.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                    bot.edit_message_text(f"📚 {sub} ({sem})\nاختر القسم:", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
            elif data.startswith("cat_"):
                cat = data.replace("cat_", "", 1)
                sem = user_data.get(cid, {}).get("semester", "")
                sub = user_data.get(cid, {}).get("subject", "")
                with db() as conn:
                    rows = conn.execute("SELECT DISTINCT title FROM content WHERE semester = ? AND subject = ? AND category = ?", (sem, sub, cat)).fetchall()
                m = InlineKeyboardMarkup()
                for r in rows:
                    m.add(InlineKeyboardButton(f"📖 {r['title']}", callback_data=f"lec_{r['title']}"))
                m.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                bot.edit_message_text(f"📚 {sub} ➔ {cat}\nاختر المحاضرة:", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
            elif data.startswith("lec_"):
                lec = data.replace("lec_", "", 1)
                user_data.setdefault(cid, {})["current_lecture"] = lec
                m = InlineKeyboardMarkup()
                m.add(InlineKeyboardButton("📄 عرض المحتوى", callback_data="show_all"))
                m.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                bot.edit_message_text(f"📖 المحاضرة: {lec}", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
            elif data == "show_all":
                sem = user_data.get(cid, {}).get("semester", "")
                sub = user_data.get(cid, {}).get("subject", "")
                lec = user_data.get(cid, {}).get("current_lecture", "")
                with db() as conn:
                    rows = conn.execute("SELECT * FROM content WHERE semester = ? AND subject = ? AND title = ?", (sem, sub, lec)).fetchall()
                for r in rows:
                    cap = f"🎓 {r['semester']}\n📚 {r['subject']}\n📖 {r['title']}\n📂 {r['category']}\n👨‍🏫 {r['doctor']}"
                    if r['content_type'] == "text":
                        bot.send_message(cid, cap + "\n\n" + r['text_content'])
                    elif r['content_type'] == "photo":
                        bot.send_photo(cid, r['file_id'], caption=cap)
                    elif r['content_type'] == "document":
                        bot.send_document(cid, r['file_id'], caption=cap)
                    elif r['content_type'] == "video":
                        bot.send_video(cid, r['file_id'], caption=cap)
            elif data.startswith("replyq_") and cid == ADMIN_ID:
                qid = int(data.split("_")[1])
                user_states[cid] = f"replying_q_{qid}"
                bot.send_message(cid, f"💬 اكتب إجابتك للسؤال رقم ({qid}) الآن مباشرة في رسالة:")
            bot.answer_callback_query(c.id)
        except Exception as e:
            logger.error(e)

    @bot.message_handler(func=lambda m: True, content_types=["text", "document", "video", "photo", "audio", "voice"])
    def all_msgs(m):
        cid = m.chat.id
        uid = m.from_user.id
        txt = m.text.strip() if m.text else ""
        st = user_states.get(cid)

        if st and st.startswith("replying_q_") and cid == ADMIN_ID:
            qid = int(st.replace("replying_q_", ""))
            with db() as conn:
                row = conn.execute("SELECT user_id, question FROM questions WHERE id = ?", (qid,)).fetchone()
                if row:
                    conn.execute("UPDATE questions SET answer = ?, status = 'تمت الإجابة' WHERE id = ?", (txt, qid))
                    try:
                        bot.send_message(row["user_id"], f"🔔 تمت الإجابة على سؤالك رقم ({qid}):\n\n❓ السؤال: {row['question']}\n\n💬 الإجابة:\n{txt}")
                    except Exception:
                        pass
                    bot.send_message(cid, f"✅ تم إرسال الإجابة بنجاح للطالب على السؤال رقم ({qid}).", reply_markup=kb(ADMIN_ITEMS))
            user_states.pop(cid, None)
            return

        if st == "admin_save_new_subject" and cid == ADMIN_ID:
            sem = user_data.get(cid, {}).get("new_sub_sem", "")
            if txt and sem:
                try:
                    with db() as conn:
                        conn.execute("INSERT OR IGNORE INTO custom_subjects (semester, name) VALUES (?, ?)", (sem, txt))
                    bot.send_message(cid, f"✅ تمت إضافة المادة ({txt}) إلى ({sem}) بنجاح!", reply_markup=kb(ADMIN_ITEMS))
                except Exception:
                    bot.send_message(cid, "⚠️ حدث خطأ أو أن المادة موجودة مسبقاً.", reply_markup=kb(ADMIN_ITEMS))
            user_states.pop(cid, None)
            return

        if st == "admin_add_doc" and cid == ADMIN_ID:
            user_data.setdefault(cid, {})["doctor"] = "" if txt == "لا يوجد" else txt
            user_states[cid] = "admin_add_title"
            bot.send_message(cid, "📝 اكتب عنوان المحاضرة أو الملف (مثال: المحاضرة الأولى):")
            return

        if st == "admin_add_title" and cid == ADMIN_ID:
            user_data.setdefault(cid, {})["title"] = txt
            user_states[cid] = "admin_add_notes"
            bot.send_message(cid, "📌 اكتب ملاحظات (أو أرسل: لا يوجد):")
            return

        if st == "admin_add_notes" and cid == ADMIN_ID:
            user_data.setdefault(cid, {})["notes"] = "" if txt == "لا يوجد" else txt
            user_states[cid] = "admin_add_file"
            bot.send_message(cid, "📎 أرسل الملف الآن (PDF، صورة، فيديو، أو نص):")
            return

        if st == "admin_add_file" and cid == ADMIN_ID:
            d = user_data.get(cid, {})
            ctype = m.content_type
            fid = ""
            if ctype == "photo":
                fid = m.photo[-1].file_id
            elif ctype in ["document", "video", "audio", "voice"]:
                fid = getattr(m, ctype).file_id

            with db() as conn:
                conn.execute(
                    "INSERT INTO content (semester, subject, category, doctor, title, notes, content_type, file_id, text_content) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (d.get("semester"), d.get("subject"), d.get("category"), d.get("doctor"), d.get("title"), d.get("notes"), ctype, fid, txt if ctype == "text" else "")
                )
            bot.send_message(cid, "✅ تمت إضافة المحتوى بنجاح!", reply_markup=kb(ADMIN_ITEMS))
            user_states.pop(cid, None)
            user_data.pop(cid, None)
            return

        if st == "ask_q":
            with db() as conn:
                cur = conn.execute("INSERT INTO questions (user_id, username, question) VALUES (?, ?, ?)", (m.from_user.id, m.from_user.username or "", txt))
                qid = cur.lastrowid
            bot.send_message(cid, f"✅ تم إرسال سؤالك برقم: {qid}", reply_markup=kb(HOME_ITEMS))
            if ADMIN_ID != 0:
                m_reply = InlineKeyboardMarkup()
                m_reply.add(InlineKeyboardButton("💬 رد على هذا السؤال", callback_data=f"replyq_{qid}"))
                bot.send_message(ADMIN_ID, f"❓ سؤال جديد رقم #{qid}\n👤 من الطالب: {m.from_user.first_name}\n\n📝 السؤال:\n{txt}", reply_markup=m_reply)
            user_states.pop(cid, None)
    