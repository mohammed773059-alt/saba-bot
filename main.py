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

# --- الكيبورد السفلي الثابت (للأوامر العامة) ---
def main_reply_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("📚 المواد التعليمية"),
        telebot.types.KeyboardButton("📎 ملحقات"),
        telebot.types.KeyboardButton("📅 جدول المحاضرات"),
        telebot.types.KeyboardButton("❓ طرح سؤال"),
        telebot.types.KeyboardButton("🔔 التذكيرات"),
        telebot.types.KeyboardButton("📊 متابعة الأسئلة"),
        telebot.types.KeyboardButton("👨‍💻 مطور البوت")
    )
    return markup

# --- أزرار رسائل المواد (Inline) داخل المحادثة ---
def inline_materials_menu():
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("مهارة اللغة العربية 📖", callback_data="mat_arabic"),
        telebot.types.InlineKeyboardButton("مهارة اللغة الإنجليزية 📖", callback_data="mat_english"),
        telebot.types.InlineKeyboardButton("التفاضل والتكامل 📐", callback_data="mat_math"),
        telebot.types.InlineKeyboardButton("الفيزياء العامة وحوسبة ⚛️", callback_data="mat_physics"),
        telebot.types.InlineKeyboardButton("مقدمة في الحوسبة 💻", callback_data="mat_intro"),
        telebot.types.InlineKeyboardButton("مهارات الحاسوب ⌨️", callback_data="mat_skills"),
        telebot.types.InlineKeyboardButton("⬅️ رجوع للقائمة الرئيسية", callback_data="main_menu")
    )
    return markup

# --- أزرار أقسام المادة داخل الرسالة (Inline) ---
def inline_sections_menu(mat_code):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("📖 المحاضرات", callback_data=f"sec_lectures_{mat_code}"),
        telebot.types.InlineKeyboardButton("🎥 شروحات فيديو", callback_data=f"sec_videos_{mat_code}"),
        telebot.types.InlineKeyboardButton("📝 التكاليف", callback_data=f"sec_homework_{mat_code}"),
        telebot.types.InlineKeyboardButton("📄 ملفات PDF", callback_data=f"sec_pdf_{mat_code}"),
        telebot.types.InlineKeyboardButton("📎 الملحقات", callback_data=f"sec_attachments_{mat_code}"),
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
        f"أهلاً بك يا مهندس {user_name} في بوت قسم تكنولوجيا المعلومات (IT) - موازي 🎓\n\n"
        f"اختر من القائمة أدناه:"
    )
    bot.reply_to(message, welcome_text, reply_markup=main_reply_keyboard())

# 4. معالجة الرسائل والأزرار السفلية
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text

    if user_states.get(user_id) == "waiting_for_question":
        user_states[user_id] = None
        bot.reply_to(message, "✅ **تم إرسال سؤالك بنجاح!**\nسيتم مراجعته والرد عليك قريباً.", reply_markup=main_reply_keyboard())
        if ADMIN_ID:
            try:
                bot.send_message(ADMIN_ID, f"📩 سؤال جديد من الطالب [{message.from_user.first_name}]:\n\n{text}")
            except Exception:
                pass
        return

    if text == "📚 المواد التعليمية":
        bot.send_message(message.chat.id, "📚 **اختر المادة التعليمية:**", reply_markup=inline_materials_menu())

    elif text == "📎 ملحقات":
        bot.send_message(message.chat.id, "📎 **قسم الملحقات العامة:**\nاختر المادة لعرض ملحقاتها:", reply_markup=inline_materials_menu())

    elif text == "📅 جدول المحاضرات":
        bot.reply_to(message, "📅 **جدول المحاضرات الدراسية:**\n[يمكنك إرسال ملف الجدول بصيغة PDF هنا ليظهر للجميع]")

    elif text == "❓ طرح سؤال":
        user_states[user_id] = "waiting_for_question"
        bot.reply_to(message, "❓ **طرح سؤال:**\nاكتب سؤالك الآن في رسالة واحدة وسيقوم البوت باستلامه:")

    elif text == "🔔 التذكيرات":
        bot.reply_to(message, "🔔 **قسم التذكيرات:**\nلا توجد تذكيرات جديدة في الوقت الحالي.")

    elif text == "📊 متابعة الأسئلة":
        bot.reply_to(message, "📊 **متابعة الأسئلة:**\nهنا يتم عرض وتتبع حالة الأسئلة والاستفسارات الخاصة بك.")

    elif text == "👨‍💻 مطور البوت":
        bot.reply_to(message, "👨‍💻 **مطور البوت:**\nالمهندس: **محمد الظاهر** 🚀")

    else:
        bot.reply_to(message, f"تم استلام رسالتك: {text}", reply_markup=main_reply_keyboard())

# 5. معالجة الضغط على الأزرار الشفافة داخل الرسائل (Inline Callbacks)
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if data == "main_menu":
        bot.edit_message_text("🏠 **القائمة الرئيسية:**\nاختر من الأزرار السفلية أو اضغط خياراً جديداً.", chat_id=chat_id, message_id=message_id)
        
    elif data == "back_to_materials" or data == "mat_menu":
        bot.edit_message_text("📚 **اختر المادة التعليمية:**", chat_id=chat_id, message_id=message_id, reply_markup=inline_materials_menu())

    # تفاصيل المواد والتحويل لأقسامها
    elif data.startswith("mat_"):
        mat_names = {
            "mat_arabic": "مهارة اللغة العربية",
            "mat_english": "مهارة اللغة الإنجليزية",
            "mat_math": "التفاضل والتكامل",
            "mat_physics": "الفيزياء العامة وحوسبة",
            "mat_intro": "مقدمة في الحوسبة",
            "mat_skills": "مهارات الحاسوب"
        }
        subject_name = mat_names.get(data, "المادة")
        bot.edit_message_text(f"📚 **{subject_name}**\nاختر القسم الدراسي المطلوب:", chat_id=chat_id, message_id=message_id, reply_markup=inline_sections_menu(data))

    # الأقسام الداخلية للمادة (محاضرات، فيديو، تكاليف...)
    elif data.startswith("sec_"):
        parts = data.split("_")
        section_type = parts[1]
        
        sec_titles = {
            "lectures": "📖 المحاضرات",
            "videos": "🎥 شروحات فيديو",
            "homework": "📝 التكاليف",
            "pdf": "📄 ملفات PDF",
            "attachments": "📎 الملحقات"
        }
        title = sec_titles.get(section_type, "القسم")
        bot.edit_message_text(f"📁 **{title}**\nسيتم إدراج الملفات والمحتويات هنا تباعاً.", chat_id=chat_id, message_id=message_id, reply_markup=inline_sections_menu(parts[2]))

if __name__ == "__main__":
    keep_alive()
    print("Bot is starting...")
    bot.polling(none_stop=True)
