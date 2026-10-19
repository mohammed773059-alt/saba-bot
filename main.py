import os
import telebot
from flask import Flask
from threading import Thread

# 1. إعداد سيرفر Web للحفاظ على نشاط البوت على Render
app = Flask('')

@app.route('/')
def home():
    return "IT Parallel Bot is running smoothly!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. قراءة المتغيرات وتأسيس البوت
TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

bot = telebot.TeleBot(TOKEN)
user_states = {}
admin_upload_cache = {}
DYNAMIC_CONTENT = {}

# --- الكيبورد السفلي الثابت ---
def main_reply_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("📚 المواد التعليمية"),
        telebot.types.KeyboardButton("📎 ملحقات"),
        telebot.types.KeyboardButton("❓ طرح سؤال"),
        telebot.types.KeyboardButton("📅 جدول المحاضرات"),
        telebot.types.KeyboardButton("📊 متابعة الأسئلة"),
        telebot.types.KeyboardButton("🔔 التذكيرات"),
        telebot.types.KeyboardButton("👨‍💻 مطور البوت")
    )
    return markup

# --- أزرار المواد الشفافة (Inline) ---
def inline_materials_menu(prefix="mat"):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("مهارة اللغة العربية 📖", callback_data=f"{prefix}_arabic"),
        telebot.types.InlineKeyboardButton("مهارة اللغة الإنجليزية 📖", callback_data=f"{prefix}_english"),
        telebot.types.InlineKeyboardButton("التفاضل والتكامل 📐", callback_data=f"{prefix}_math"),
        telebot.types.InlineKeyboardButton("الفيزياء العامة وحوسبة ⚛️", callback_data=f"{prefix}_physics"),
        telebot.types.InlineKeyboardButton("مقدمة في الحوسبة 💻", callback_data=f"{prefix}_intro"),
        telebot.types.InlineKeyboardButton("مهارات الحاسوب ⌨️", callback_data=f"{prefix}_skills"),
        telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
    )
    return markup

# --- أزرار أقسام المادة الشفافة (Inline) ---
def inline_sections_menu(mat_code, prefix="sec"):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("📖 المحاضرات", callback_data=f"{prefix}_lectures_{mat_code}"),
        telebot.types.InlineKeyboardButton("🎥 شروحات فيديو", callback_data=f"{prefix}_videos_{mat_code}"),
        telebot.types.InlineKeyboardButton("📝 التكاليف", callback_data=f"{prefix}_homework_{mat_code}"),
        telebot.types.InlineKeyboardButton("📄 ملفات PDF", callback_data=f"{prefix}_pdf_{mat_code}"),
        telebot.types.InlineKeyboardButton("📎 الملحقات", callback_data=f"{prefix}_attachments_{mat_code}"),
        telebot.types.InlineKeyboardButton("↩️ رجوع للمواد", callback_data="back_to_materials"),
        telebot.types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
    )
    return markup

# 3. معالج الأمر /start
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_name = message.from_user.first_name
    user_states[message.from_user.id] = None
    welcome_text = (
        f"أهلاً بك مجدداً يا مهندس {user_name}!\n"
        f"👥 مجموعتك الدراسية الحالية: تكنولوجيا المعلومات موازي (IT)\n\n"
        f"اختر الخدمة المطلوبة من القائمة أدناه:"
    )
    bot.reply_to(message, welcome_text, reply_markup=main_reply_keyboard())

# 4. معالج أمر /admin الخاص بك
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    if ADMIN_ID and str(user_id) == str(ADMIN_ID):
        admin_text = (
            "🛠️ **لوحة تحكم الأدمن (المهندس محمد):**\n\n"
            "لإدراج محاضرة أو ملف جديد:\n"
            "1. قم بإرسال الملف أو الفيديو أو النص مباشرة هنا في البوت.\n"
            "2. سيطلب منك البوت اختيار المادة والقسم لنشره فوراً للطلاب."
        )
        bot.reply_to(message, admin_text, parse_mode="Markdown")
    else:
        bot.reply_to(message, "⚠️ عذراً، هذا الأمر مخصص لمطور البوت فقط.")

# 5. معالجة الرسائل والمدخلات
@bot.message_handler(content_types=['text', 'document', 'video', 'audio', 'photo'])
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text if message.text else ""

    if text == "/cancel":
        user_states[user_id] = None
        admin_upload_cache.pop(user_id, None)
        bot.reply_to(message, "❌ تم إلغاء العملية.", reply_markup=main_reply_keyboard())
        return

    # استقبال الملفات من الأدمن لرفعها
    if ADMIN_ID and str(user_id) == str(ADMIN_ID):
        if message.content_type != 'text' or (text and not text.startswith('/') and user_states.get(user_id) != "waiting_for_question"):
            admin_upload_cache[user_id] = message
            bot.reply_to(message, "📥 **تم استقبال الملف بنجاح!**\nالآن اختر المادة التي تريد إدراج هذا المحتوى لها:", reply_markup=inline_materials_menu(prefix="upmat"))
            return

    if user_states.get(user_id) == "waiting_for_question":
        user_states[user_id] = None
        bot.reply_to(message, "✅ تم إرسال سؤالك بنجاح!\nسيتم مراجعته والرد عليك قريباً.", reply_markup=main_reply_keyboard())
        if ADMIN_ID:
            try:
                bot.send_message(ADMIN_ID, f"📩 سؤال جديد من الطالب [{message.from_user.first_name}]:\n\n{text}")
            except Exception:
                pass
        return

    if text == "📚 المواد التعليمية" or text == "📎 ملحقات":
        bot.send_message(message.chat.id, "📚 **اختر المادة التعليمية:**", parse_mode="Markdown", reply_markup=inline_materials_menu(prefix="mat"))

    elif text == "📅 جدول المحاضرات":
        db_key = "schedule_pdf"
        if db_key in DYNAMIC_CONTENT:
            saved_msg = DYNAMIC_CONTENT[db_key]
            bot.copy_message(chat_id=message.chat.id, from_chat_id=saved_msg.chat.id, message_id=saved_msg.message_id)
        else:
            schedule_text = (
                "📅 **جدول المحاضرات الدراسية**\n"
                "قسم تقنية المعلومات (IT - موازي)\n\n"
                "⏳ **سيتم إدراج جدول المحاضرات PDF قريباً.**"
            )
            bot.reply_to(message, schedule_text, parse_mode="Markdown", reply_markup=main_reply_keyboard())

    elif text == "❓ طرح سؤال":
        user_states[user_id] = "waiting_for_question"
        question_prompt = (
            "❓ **قم بكتابة السؤال الذي تريد طرحه:**\n\n"
            "(يمكنك إرسال `/cancel` في أي وقت للإلغاء)"
        )
        bot.reply_to(message, question_prompt, parse_mode="Markdown")

    elif text == "🔔 التذكيرات":
        bot.reply_to(message, "🔔 You do not have any reminders.", reply_markup=main_reply_keyboard())

    elif text == "📊 متابعة الأسئلة":
        status_text = (
            "📊 **سجل أسئلتك وحالتها:**\n\n"
            "-----------------------------------\n"
            "🕒 **التاريخ:** PM 06:03 15-10-2026\n"
            "❓ **السؤال:** متابعة الأسئلة\n"
            "📌 **الحالة:** قيد انتظار رد المدرس\n"
            "-----------------------------------"
        )
        bot.reply_to(message, status_text, parse_mode="Markdown", reply_markup=main_reply_keyboard())

    elif text == "👨‍💻 مطور البوت":
        bot.reply_to(message, "👨‍💻 **مطور البوت:** المهندس محمد الظاهر 🚀", reply_markup=main_reply_keyboard())

    else:
        if text and not text.startswith('/'):
            pass

# 6. معالجة الأزرار الشفافة وفورية الاستجابة (0 ثانية)
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    bot.answer_callback_query(call.id)
    
    data = call.data
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    mat_names = {
        "arabic": "مهارة اللغة العربية",
        "english": "مهارة اللغة الإنجليزية",
        "math": "التفاضل والتكامل",
        "physics": "الفيزياء العامة وحوسبة",
        "intro": "مقدمة في الحوسبة",
        "skills": "مهارات الحاسوب"
    }

    if data == "main_menu":
        bot.send_message(chat_id, "🏠 **القائمة الرئيسية:**", parse_mode="Markdown", reply_markup=main_reply_keyboard())
        
    elif data == "back_to_materials":
        bot.send_message(chat_id, "📚 **اختر المادة التعليمية:**", parse_mode="Markdown", reply_markup=inline_materials_menu(prefix="mat"))

    # خطوات رفع الآدمن للمادة
    elif data.startswith("upmat_"):
        mat_code = data.split("_")[1]
        admin_upload_cache[f"{user_id}_mat"] = mat_code
        bot.send_message(chat_id, f"تم اختيار المادة: **{mat_names.get(mat_code)}**\nاختر القسم المراد الإدراج له:", parse_mode="Markdown", reply_markup=inline_sections_menu(mat_code, prefix="upsec"))

    # حفظ المحتوى للقسم المحدد
    elif data.startswith("upsec_"):
        parts = data.split("_")
        sec_type = parts[1]
        mat_code = parts[2]
        
        cached_msg = admin_upload_cache.get(user_id)
        if cached_msg:
            db_key = f"{mat_code}_{sec_type}"
            DYNAMIC_CONTENT[db_key] = cached_msg
            bot.send_message(chat_id, f"✅ **تم إدراج المحتوى بنجاح في ({mat_names.get(mat_code)} ⟵ {sec_type})!**", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "⚠️ انتهت المهلة، أرسل الملف مرة أخرى.")
        return

    elif data.startswith("mat_"):
        mat_code = data.split("_")[1]
        subject_name = mat_names.get(mat_code, "المادة")
        bot.send_message(chat_id, f"📚 **{subject_name}**\nاختر القسم الدراسي المطلوب:", parse_mode="Markdown", reply_markup=inline_sections_menu(mat_code, prefix="sec"))

    elif data.startswith("sec_"):
        parts = data.split("_")
        sec_type = parts[1]
        mat_code = parts[2]

        sec_titles = {
            "lectures": "📖 المحاضرات",
            "videos": "🎥 شروحات فيديو",
            "homework": "📝 التكاليف",
            "pdf": "📄 ملفات PDF",
            "attachments": "📎 الملحقات"
        }
        title = sec_titles.get(sec_type, "القسم")
        db_key = f"{mat_code}_{sec_type}"

        if db_key in DYNAMIC_CONTENT:
            saved_msg = DYNAMIC_CONTENT[db_key]
            bot.copy_message(chat_id=chat_id, from_chat_id=saved_msg.chat.id, message_id=saved_msg.message_id)
        else:
            bot.send_message(chat_id, f"📁 **{title}**\n\n⏳ **سوف يتم إدراج المحاضرات والمحتويات قريباً.**", parse_mode="Markdown")

if __name__ == "__main__":
    keep_alive()
    print("Bot is working...")
    bot.polling(none_stop=True)
