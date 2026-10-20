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

SUBJECTS = [
    "مهارة اللغة العربية", "مهارة اللغة الإنجليزية",
    "التفاضل والتكامل", "الفيزياء العامة وحوسبة",
    "مقدمة في الحوسبة", "مهارات الحاسوب"
]

CATEGORIES = ["المحاضرات", "شروحات فيديو", "التكاليف", "ملفات PDF", "الملحقات"]

HOME_ITEMS = [
    "📚 المواد التعليمية", "📎 الملحقات", "📅 الجدول الدراسي",
    "❓ طرح السؤال", "💬 متابعة السؤال", "🔔 التذكيرات", "👨‍💻 مطور البوت"
]

ADMIN_ITEMS = ["➕ إضافة محتوى", "📅 رفع الجدول الدراسي", "💬 أسئلة الطلاب", "🏠 القائمة الرئيسية"]
ADMIN_AFTER = ["➕ إضافة محتوى آخر", "⚙️ لوحة الإدارة", "🏠 القائمة الرئيسية"]

user_states = {}
user_data = {}

def db():
    c = sqlite3.connect(DB_FILE, timeout=30)
    c.row_factory = sqlite3.Row
    return c

with db() as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS content (id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT, category TEXT, doctor TEXT, title TEXT, notes TEXT, content_type TEXT, file_id TEXT, text_content TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, content_type TEXT, file_id TEXT, text_content TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, question TEXT, answer TEXT, status TEXT DEFAULT 'قيد المراجعة')")
    conn.execute("CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, reminder TEXT)")

def kb(items, cols=2):
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=cols)
    for i in range(0, len(items), cols):
        m.row(*[KeyboardButton(x) for x in items[i:i+cols]])
    return m

def send_home(chat_id):
    user_states.pop(chat_id, None)
    user_data.pop(chat_id, None)
    if bot:
        bot.send_message(chat_id, "🎓 كلية تكنولوجيا المعلومات\n💻 قسم تكنولوجيا المعلومات (IT) - موازي\n\nاختر الخدمة:", reply_markup=kb(HOME_ITEMS))

if bot:
    @bot.message_handler(commands=["start"])
    def start(m):
        send_home(m.chat.id)

    @bot.message_handler(commands=["admin"], func=lambda m: m.from_user.id == ADMIN_ID)
    @bot.message_handler(func=lambda m: m.text in ["admin", "ادمن", "⚙️ لوحة الإدارة"] and m.from_user.id == ADMIN_ID)
    def admin_p(m):
        user_states[m.chat.id] = "admin_menu"
        bot.send_message(m.chat.id, "🔐 لوحة الإدارة:", reply_markup=kb(ADMIN_ITEMS))

    @bot.callback_query_handler(func=lambda c: True)
    def cb(c):
        cid = c.message.chat.id
        data = c.data
        try:
            if data == "go_home":
                send_home(cid)
            elif data.startswith("replyq_") and cid == ADMIN_ID:
                qid = int(data.split("_")[1])
                user_states[cid] = f"replying_q_{qid}"
                bot.send_message(cid, f"💬 اكتب إجابتك للسؤال رقم ({qid}) الآن مباشرة في رسالة:")
            elif data.startswith("sub_") or data.startswith("submat_"):
                is_att = data.startswith("submat_")
                idx = int(data.split("_")[1])
                sub = SUBJECTS[idx]
                user_data.setdefault(cid, {})["subject"] = sub
                m = InlineKeyboardMarkup()
                if is_att:
                    with db() as conn:
                        rows = conn.execute("SELECT DISTINCT title FROM content WHERE subject = ? AND category = 'الملحقات'", (sub,)).fetchall()
                    if not rows:
                        m.add(InlineKeyboardButton("🔄 رجوع", callback_data="back_submat"), InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                        bot.edit_message_text(f"📎 ملحقات مادة: {sub}\n\n⏳ لا توجد ملحقات.", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
                    else:
                        for r in rows:
                            m.add(InlineKeyboardButton(f"📖 {r['title']}", callback_data=f"attlec_{r['title']}"))
                        m.add(InlineKeyboardButton("🔄 رجوع", callback_data="back_submat"), InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                        bot.edit_message_text(f"📎 ملحقات مادة: {sub}\nاختر المحاضرة:", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
                else:
                    for cat in CATEGORIES:
                        m.add(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
                    m.add(InlineKeyboardButton("🔄 رجوع", callback_data="back_sub"), InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                    bot.edit_message_text(f"📚 {sub}\nاختر القسم:", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
            elif data == "back_sub" or data == "back_submat":
                m = InlineKeyboardMarkup()
                for i, s in enumerate(SUBJECTS):
                    m.add(InlineKeyboardButton(s, callback_data=f"sub_{i}" if data == "back_sub" else f"submat_{i}"))
                m.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                bot.edit_message_text("📚 اختر المادة:", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
            elif data.startswith("cat_"):
                cat = data.replace("cat_", "", 1)
                sub = user_data.get(cid, {}).get("subject", "")
                with db() as conn:
                    rows = conn.execute("SELECT DISTINCT title FROM content WHERE subject = ? AND category = ?", (sub, cat)).fetchall()
                m = InlineKeyboardMarkup()
                for r in rows:
                    m.add(InlineKeyboardButton(f"📖 {r['title']}", callback_data=f"lec_{r['title']}"))
                m.add(InlineKeyboardButton("🔄 رجوع", callback_data="back_cats"), InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                bot.edit_message_text(f"📚 {sub} ➔ {cat}\nاختر المحاضرة:", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
            elif data.startswith("lec_"):
                lec = data.replace("lec_", "", 1)
                user_data.setdefault(cid, {})["current_lecture"] = lec
                m = InlineKeyboardMarkup()
                m.add(InlineKeyboardButton("📄 عرض المحتوى", callback_data="show_all"))
                m.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
                bot.edit_message_text(f"📖 المحاضرة: {lec}", chat_id=cid, message_id=c.message.message_id, reply_markup=m)
            elif data == "show_all":
                sub = user_data.get(cid, {}).get("subject", "")
                lec = user_data.get(cid, {}).get("current_lecture", "")
                with db() as conn:
                    rows = conn.execute("SELECT * FROM content WHERE subject = ? AND title = ?", (sub, lec)).fetchall()
                for r in rows:
                    cap = f"📚 {r['subject']}\n📖 {r['title']}\n📂 {r['category']}\n👨‍🏫 {r['doctor']}"
                    if r['content_type'] == "text":
                        bot.send_message(cid, cap + "\n\n" + r['text_content'])
                    elif r['content_type'] == "photo":
                        bot.send_photo(cid, r['file_id'], caption=cap)
                    elif r['content_type'] == "document":
                        bot.send_document(cid, r['file_id'], caption=cap)
                    elif r['content_type'] == "video":
                        bot.send_video(cid, r['file_id'], caption=cap)
            bot.answer_callback_query(c.id)
        except Exception as e:
            logger.error(e)

    @bot.message_handler(func=lambda m: True, content_types=["text", "document", "video", "photo", "audio", "voice"])
    def all_msgs(m):
        cid = m.chat.id
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
            return

        if st == "up_sched":
            with db() as conn:
                conn.execute("INSERT OR REPLACE INTO settings (key, content_type, file_id, text_content) VALUES ('schedule', ?, ?, ?)", 
                             (m.content_type, m.photo[-1].file_id if m.content_type == "photo" else (m.document.file_id if m.content_type == "document" else ""), txt))
            bot.send_message(cid, "✅ تم رفع الجدول.", reply_markup=kb(ADMIN_ITEMS))
            user_states.pop(cid, None)
            return

        if txt == "📚 المواد التعليمية":
            m_markup = InlineKeyboardMarkup()
            for i, s in enumerate(SUBJECTS):
                m_markup.add(InlineKeyboardButton(s, callback_data=f"sub_{i}"))
            m_markup.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
            bot.send_message(cid, "📚 اختر المادة:", reply_markup=m_markup)
        elif txt == "📎 الملحقات":
            m_markup = InlineKeyboardMarkup()
            for i, s in enumerate(SUBJECTS):
                m_markup.add(InlineKeyboardButton(s, callback_data=f"submat_{i}"))
            m_markup.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="go_home"))
            bot.send_message(cid, "📎 اختر المادة لعرض ملحقاتها:", reply_markup=m_markup)
        elif txt == "📅 الجدول الدراسي":
            with db() as conn:
                s = conn.execute("SELECT * FROM settings WHERE key = 'schedule'").fetchone()
            if not s:
                bot.send_message(cid, "📅 الجدول الدراسي غير متوفر حالياً.\n⏳ سوف يتم إدراجه قريباً من قبل إدارة البوت.")
            else:
                if s["content_type"] == "text":
                    bot.send_message(cid, s["text_content"])
                elif s["content_type"] == "photo":
                    bot.send_photo(cid, s["file_id"])
                elif s["content_type"] == "document":
                    bot.send_document(cid, s["file_id"])
        elif txt == "❓ طرح السؤال":
            user_states[cid] = "ask_q"
            bot.send_message(cid, "❓ اكتب سؤالك في رسالة واحدة:", reply_markup=kb(["🏠 القائمة الرئيسية"]))
        elif txt == "💬 متابعة السؤال":
            with db() as conn:
                rows = conn.execute("SELECT * FROM questions WHERE user_id = ? ORDER BY id DESC LIMIT 5", (m.from_user.id,)).fetchall()
            if not rows:
                bot.send_message(cid, "ℹ️ ليس لديك أسئلة.")
            for r in rows:
                bot.send_message(cid, f"❓ سؤال #{r['id']}: {r['question']}\n📌 الحالة: {r['status']}\n💬 الإجابة: {r['answer'] or 'قيد المراجعة'}")
        elif txt == "🔔 التذكيرات":
            bot.send_message(cid, "🔔 لا توجد تذكيرات جديدة حالياً.")
        elif txt == "👨‍💻 مطور البوت":
            bot.send_message(cid, "👨‍💻 مطور البوت:\nالمهندس / محمد الظاهر\n📞 718117501")
        elif txt in ["➕ إضافة محتوى", "➕ إضافة محتوى آخر"] and m.from_user.id == ADMIN_ID:
            m_markup = InlineKeyboardMarkup()
            for i, s in enumerate(SUBJECTS):
                m_markup.add(InlineKeyboardButton(s, callback_data=f"admin_sub_{i}"))
            bot.send_message(cid, "📚 اختر المادة لإضافة المحتوى:", reply_markup=m_markup)
        elif txt == "📅 رفع الجدول الدراسي" and m.from_user.id == ADMIN_ID:
            user_states[cid] = "up_sched"
            bot.send_message(cid, "📅 أرسل الجدول الجديد (صورة أو ملف):")
        elif txt == "💬 أسئلة الطلاب" and m.from_user.id == ADMIN_ID:
            with db() as conn:
                rows = conn.execute("SELECT * FROM questions ORDER BY id DESC LIMIT 5").fetchall()
            if not rows:
                bot.send_message(cid, "لا توجد أسئلة.")
            for r in rows:
                m_reply = InlineKeyboardMarkup()
                m_reply.add(InlineKeyboardButton("💬 رد على هذا السؤال", callback_data=f"replyq_{r['id']}"))
                bot.send_message(cid, f"❓ سؤال #{r['id']} من الطالب ({r['user_id']}):\n\n📝 السؤال:\n{r['question']}\n📌 الحالة: {r['status']}", reply_markup=m_reply)
        elif txt == "🏠 القائمة الرئيسية":
            send_home(cid)

def run_bot():
    if bot:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)

if bot:
    threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)