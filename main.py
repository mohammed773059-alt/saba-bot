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

# --- الكيبورد السفلي الثابت (مع عكس الأماكن: اليمين إلى اليسار واليسار إلى اليمين) ---
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
        f"أهلاً بك مجددا مهندس {user_name}!\n"
        f"👥 مجموعتك الدراسية الحالية: تكنولوجيا المعلومات موازي (IT)[span_1](start_span)[span_1](end_span)[span_2](start_span)[span_2](end_span)\n\n"
        f"اختر الخدمة المطلوبة من القائمة أدناه:"
    )
    bot.reply_to(message, welcome_text, reply_markup=main_reply_keyboard())

# 4. معالجة الرسائل والمدخلات
@bot.message_handler(content_types=['text', 'document', 'video', 'audio', 'photo'])
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text if message.text else ""

    if text == "/cancel":
        user_states[user_id] = None
        bot.reply_to(message, "❌ تم إلغاء العملية.", reply_markup=main_reply_keyboard())
        return

    if user_states.get(user_id) == "waiting_for_question":
        user_states[user_id] = None
        bot.reply_to(message, "✅ **تم إرسال سؤالك بنجاح!**\nسيتم مراجعته والرد عليك قريباً.", reply_markup=main_reply_keyboard())
        if ADMIN_ID:
            try:
                bot.send_message(ADMIN_ID, f"📩 سؤال جديد من الطالب [{message.from_user.first_name}]:\n\n{text}")
            except Exception:
                pass
        return

    if text == "📚 المواد التعليمية" or text == "📎 ملحقات":
        bot.send_message(message.chat.id, "📚 **اختر المادة التعليمية:**", reply_markup=inline_materials_menu(prefix="mat"))

    elif text == "📅 جدول المحاضرات":
        schedule_text = (
            "📅 **جدول المحاضرات الدراسية**\n"
            "قسم تقنية المعلومات (IT - موازي)[span_3](start_span)[span_3](end_span)\n\n"
            "📎 [اضغط هنا لتحميل ملف جدول المحاضرات PDF]"
        )
        bot.reply_to(message, schedule_text, parse_mode="Markdown", reply_markup=main_reply_keyboard())

    elif text == "❓ طرح سؤال":
        user_states[user_id] = "waiting_for_question"
        question_prompt = (
            "❓ **قم بكتابة السؤال الذي تريد طرحه:**\n\n"
            "(يمكنك إرسال `/cancel` في أي وقت للإلغاء)[span_4](start_span)[span_4](end_span)"
        )
        bot.reply_to(message, question_prompt, parse_mode="Markdown")

    elif text == "🔔 التذكيرات":
        bot.reply_to(message, "🔔 You do not have any reminders.", reply_markup=main_reply_keyboard())[span_5](start_span)[span_5](end_span)

    elif text == "📊 متابعة الأسئلة":
        status_text = (
            "📊 **سجل أسئلتك وحالتها:**\n\n"
            "-----------------------------------\n"
            "🕒 **التاريخ:** PM 06:03 15-10-2026[span_6](start_span)[span_6](end_span)\n"
            "❓ **السؤال:** متابعة الأسئلة[span_7](start_span)[span_7](end_span)\n"
            "📌 **الحالة:** قيد انتظار رد المدرس[span_8](start_span)[span_8](end_span)\n"
            "-----------------------------------"
        )
        bot.reply_to(message, status_text, parse_mode="Markdown", reply_markup=main_reply_keyboard())

    elif text == "👨‍💻 مطور البوت":
        bot.reply_to(message, "👨‍💻 **مطور البوت:** المهندس محمد الظاهر 🚀", reply_markup=main_reply_keyboard())

    else:
        if text and not text.startswith('/'):
            pass

# 5. معالجة الضغط على الأزرار الشفافة
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    chat_id = call.message.chat.id

    mat_names = {
        "arabic": "مهارة اللغة العربية",
        "english": "مهارة اللغة الإنجليزية",
        "math": "التفاضل والتكامل",
        "physics": "الفيزياء العامة وحوسبة",
        "intro": "مقدمة في الحوسبة",
        "skills": "مهارات الحاسوب"
    }

    if data == "main_menu":
        bot.send_message(chat_id, "🏠 **القائمة الرئيسية:**", reply_markup=main_reply_keyboard())
        
    elif data == "back_to_materials":
        bot.send_message(chat_id, "📚 **اختر المادة التعليمية:**", reply_markup=inline_materials_menu(prefix="mat"))

    elif data.startswith("mat_"):
        mat_code = data.split("_")[1]
        subject_name = mat_names.get(mat_code, "المادة")
        bot.send_message(chat_id, f"📚 **{subject_name}**\nاختر القسم الدراسي المطلوب:", reply_markup=inline_sections_menu(mat_code, prefix="sec"))

    elif data.startswith("sec_"):
        parts = data.split("_")
        sec_type = parts[1]

        sec_titles = {
            "lectures": "📖 المحاضرات",
            "videos": "🎥 شروحات فيديو",
            "homework": "📝 التكاليف",
            "pdf": "📄 ملفات PDF",
            "attachments": "📎 الملحقات"
        }
        title = sec_titles.get(sec_type, "القسم")
        bot.send_message(chat_id, f"📁 **{title}**\n\n⏳ **سوف يتم إدراج المحاضرات والمحتويات قريباً.**", parse_mode="Markdown")

if __name__ == "__main__":
    keep_alive()
    print("Bot is starting...")
    bot.polling(none_stop=True)
