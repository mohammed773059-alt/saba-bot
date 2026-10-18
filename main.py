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

# --- أزرار المواد (Inline) داخل المحادثة ---
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

# --- أزرار أقسام المادة داخل الرسالة (Inline) ---
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
        f"أهلاً بك يا مهندس {user_name} في بوت قسم تكنولوجيا المعلومات (IT) - موازي 🎓\n\n"
        f"اختر من القائمة أدناه للبدء:"
    )
    bot.reply_to(message, welcome_text, reply_markup=main_reply_keyboard())

# 4. استقبال رسائل وملفات الأدمن أو الطلاب
@bot.message_handler(content_types=['text', 'document', 'video', 'audio', 'photo'])
def handle_all_messages(message):
    user_id = message.from_user.id
    
    if ADMIN_ID and str(user_id) == str(ADMIN_ID):
        if message.content_type != 'text' or (message.text and not message.text.startswith('/') and user_states.get(user_id) != "waiting_for_question"):
            admin_upload_cache[user_id] = message
            bot.reply_to(message, "📥 **تم استقبال المحتوى بنجاح!**\nالآن، اختر المادة التي تريد إدراج هذا المحتوى لها:", reply_markup=inline_materials_menu(prefix="upmat"))
            return

    if user_states.get(user_id) == "waiting_for_question":
        user_states[user_id] = None
        bot.reply_to(message, "✅ **تم إرسال سؤالك بنجاح!**\nسيتم مراجعته والرد عليك قريباً.", reply_markup=main_reply_keyboard())
        if ADMIN_ID:
            try:
                bot.send_message(ADMIN_ID, f"📩 سؤال جديد من الطالب [{message.from_user.first_name}]:\n\n{message.text}")
            except Exception:
                pass
        return

    text = message.text if message.text else ""

    if text == "📚 المواد التعليمية":
        bot.send_message(message.chat.id, "📚 **اختر المادة التعليمية:**", reply_markup=inline_materials_menu(prefix="mat"))

    elif text == "📎 ملحقات":
        bot.send_message(message.chat.id, "📎 **قسم الملحقات العامة:**\nاختر المادة لعرض ملحقاتها:", reply_markup=inline_materials_menu(prefix="mat"))

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
        if text:
            bot.reply_to(message, f"تم استلام رسالتك: {text}", reply_markup=main_reply_keyboard())

# 5. معالجة الضغط على الأزرار الشفافة
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
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
        bot.send_message(chat_id, "🏠 **القائمة الرئيسية:**", reply_markup=main_reply_keyboard())
        
    elif data == "back_to_materials":
        bot.send_message(chat_id, "📚 **اختر المادة التعليمية:**", reply_markup=inline_materials_menu(prefix="mat"))

    elif data.startswith("upmat_"):
        mat_code = data.split("_")[1]
        admin_upload_cache[f"{user_id}_mat"] = mat_code
        bot.send_message(chat_id, f"لقد اخترت مادة: **{mat_names.get(mat_code)}**\nالآن اختر القسم الذي تود إدراج المحتوى فيه:", reply_markup=inline_sections_menu(mat_code, prefix="upsec"))

    elif data.startswith("upsec_"):
        parts = data.split("_")
        sec_type = parts[1]
        mat_code = parts[2]
        
        cached_msg = admin_upload_cache.get(user_id)
        if cached_msg:
            db_key = f"{mat_code}_{sec_type}"
            DYNAMIC_CONTENT[db_key] = cached_msg
            bot.send_message(chat_id, f"✅ **تم إدراج المحتوى بنجاح في ({mat_names.get(mat_code)} ⟵ {sec_type})!**")
        else:
            bot.send_message(chat_id, "⚠️ حدث خطأ أو انقضت المهلة، حاول إرسال الملف مرة أخرى.")
        return

    elif data.startswith("mat_"):
        mat_code = data.split("_")[1]
        subject_name = mat_names.get(mat_code, "المادة")
        bot.send_message(chat_id, f"📚 **{subject_name}**\nاختر القسم الدراسي المطلوب:", reply_markup=inline_sections_menu(mat_code, prefix="sec"))

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
    print("Bot is starting...")
    bot.polling(none_stop=True)
