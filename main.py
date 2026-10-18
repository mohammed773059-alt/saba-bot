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

# متغير مؤقت لحفظ حالة المستخدم (لمعرفة هل هو في وضع طرح سؤال)
user_states = {}

# --- القوائم الرئيسية والفرعية ---

def main_menu():
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

def materials_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("مهارة اللغة العربية"),
        telebot.types.KeyboardButton("مهارة اللغة الإنجليزية"),
        telebot.types.KeyboardButton("التفاضل والتكامل"),
        telebot.types.KeyboardButton("الفيزياء العامة وحوسبة"),
        telebot.types.KeyboardButton("مقدمة في الحوسبة"),
        telebot.types.KeyboardButton("مهارات الحاسوب"),
        telebot.types.KeyboardButton("🏠 القائمة الرئيسية")
    )
    return markup

def subject_sections_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("📖 المحاضرات"),
        telebot.types.KeyboardButton("🎥 شروحات فيديو"),
        telebot.types.KeyboardButton("📝 التكاليف"),
        telebot.types.KeyboardButton("📄 ملفات PDF"),
        telebot.types.KeyboardButton("📎 الملحقات"),
        telebot.types.KeyboardButton("⬅️ رجوع للمواد"),
        telebot.types.KeyboardButton("🏠 القائمة الرئيسية")
    )
    return markup

# 3. معالج الأمر /start
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_name = message.from_user.first_name
    user_states[message.from_user.id] = None
    welcome_text = (
        f"أهلاً بك يا مهندس {user_name} في بوت قسم تكنولوجيا المعلومات (IT) - موازي 🎓\n\n"
        f"اختر من القائمة الرئيسية أدناه:"
    )
    bot.reply_to(message, welcome_text, reply_markup=main_menu())

# 4. معالجة الأزرار والرسائل النصية
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text

    # التحقق إذا كان المستخدم في وضع طرح سؤال
    if user_states.get(user_id) == "waiting_for_question":
        user_states[user_id] = None
        bot.reply_to(message, "✅ **تم إرسال سؤالك بنجاح!**\nسيتم مراجعته والرد عليك قريباً.", reply_markup=main_menu())
        # إذا أردت تحويل السؤال للأدمن تلقائياً:
        if ADMIN_ID:
            try:
                bot.send_message(ADMIN_ID, f"📩 سؤال جديد من الطالب [{message.from_user.first_name}]:\n\n{text}")
            except Exception:
                pass
        return

    # الأزرار الرئيسية
    if text == "🏠 القائمة الرئيسية":
        user_states[user_id] = None
        bot.reply_to(message, "🏠 **القائمة الرئيسية:**", reply_markup=main_menu())

    elif text == "📚 المواد التعليمية":
        bot.reply_to(message, "📚 **اختر المادة التعليمية:**", reply_markup=materials_menu())

    elif text == "📎 ملحقات":
        bot.reply_to(message, "📎 **قسم الملحقات العامة:**\nاختر المادة لعرض ملحقاتها:", reply_markup=materials_menu())

    elif text in ["مهارة اللغة العربية", "مهارة اللغة الإنجليزية", "التفاضل والتكامل", "الفيزياء العامة وحوسبة", "مقدمة في الحوسبة", "مهارات الحاسوب"]:
        # حفظ المادة المختارة مؤقتاً وعرض الأقسام الفرعية (محاضرات، فيديو، تكاليف...)
        user_states[user_id] = text
        bot.reply_to(message, f"📚 **{text}**\nاختر القسم الدراسي المطلوب:", reply_markup=subject_sections_menu())

    elif text == "⬅️ رجوع للمواد":
        bot.reply_to(message, "📚 **اختر المادة التعليمية:**", reply_markup=materials_menu())

    # الأقسام الفرعية للمادة
    elif text in ["📖 المحاضرات", "🎥 شروحات فيديو", "📝 التكاليف", "📄 ملفات PDF", "📎 الملحقات"]:
        current_subject = user_states.get(user_id, "المادة")
        if not current_subject or current_subject in ["waiting_for_question", None]:
            current_subject = "المادة المختارة"
        bot.reply_to(message, f"📁 **{text}** الخاصة بـ ({current_subject}):\nسيتم إدراج الملفات والمحتويات هنا تباعاً.", reply_markup=subject_sections_menu())

    elif text == "📅 جدول المحاضرات":
        bot.reply_to(message, "📅 **جدول المحاضرات الدراسية:**\n[يمكنك إرسال ملف الجدول بصيغة PDF هنا ليظهر للجميع]")

    elif text == "❓ طرح سؤال":
        user_states[user_id] = "waiting_for_question"
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton("🏠 القائمة الرئيسية"))
        bot.reply_to(message, "❓ **طرح سؤال:**\nاكتب سؤالك الآن في رسالة واحدة وسيقوم البوت باستلامه وتسجيله:", reply_markup=markup)

    elif text == "🔔 التذكيرات":
        bot.reply_to(message, "🔔 **قسم التذكيرات:**\nلا توجد تذكيرات جديدة في الوقت الحالي. تابع معنا باستمرار.")

    elif text == "📊 متابعة الأسئلة":
        bot.reply_to(message, "📊 **متابعة الأسئلة:**\nهنا يتم عرض وتتبع حالة الأسئلة والاستفسارات الخاصة بك.")

    elif text == "👨‍💻 مطور البوت":
        bot.reply_to(message, "👨‍💻 **مطور البوت:**\nالمهندس: **محمد الظاهر** 🚀")

    else:
        bot.reply_to(message, f"تم استلام رسالتك: {text}", reply_markup=main_menu())

if __name__ == "__main__":
    keep_alive()
    print("Bot is starting...")
    bot.polling(none_stop=True)
