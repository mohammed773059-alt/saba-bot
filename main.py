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

# 3. القائمة الرئيسية والأزرار التفاعلية
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_name = message.from_user.first_name
    welcome_text = (
        f"أهلاً بك يا مهندس {user_name} في بوت قسم تكنولوجيا المعلومات (IT) - موازي 🎓\n\n"
        f"اختر من القائمة أدناه للبدء:"
    )
    
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    btn1 = telebot.types.KeyboardButton("📚 المواد التعليمية")
    btn2 = telebot.types.KeyboardButton("📎 ملحقات")
    btn3 = telebot.types.KeyboardButton("📅 جدول المحاضرات")
    btn4 = telebot.types.KeyboardButton("❓ طرح سؤال")
    btn5 = telebot.types.KeyboardButton("🔔 التذكيرات")
    btn6 = telebot.types.KeyboardButton("📊 متابعة الأسئلة")
    btn7 = telebot.types.KeyboardButton("👨‍💻 مطور البوت")
    
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5, btn6)
    markup.add(btn7)
    
    bot.reply_to(message, welcome_text, reply_markup=markup)

# 4. معالجة الضغط على الأزرار والرسائل النصية
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text
    
    if text == "📚 المواد التعليمية":
        materials_text = (
            "📚 **قائمة المواد التعليمية:**\n\n"
            "• مهارة اللغة العربية\n"
            "• مهارة اللغة الإنجليزية\n"
            "• فيزياء عامة للحوسبة\n"
            "• التفاضل والتكامل\n"
            "• مقدمة في الحوسبة\n"
            "• مهارات الحاسوب"
        )
        bot.reply_to(message, materials_text, parse_mode="Markdown")
    
    elif text == "📎 ملحقات":
        attachments_text = (
            "📎 **قائمة الملازم والملحقات للمواد:**\n\n"
            "• مهارة اللغة العربية\n"
            "• مهارة اللغة الإنجليزية\n"
            "• فيزياء عامة للحوسبة\n"
            "• التفاضل والتكامل\n"
            "• مقدمة في الحوسبة\n"
            "• مهارات الحاسوب"
        )
        bot.reply_to(message, attachments_text, parse_mode="Markdown")
    
    elif text == "📅 جدول المحاضرات":
        bot.reply_to(message, "📅 **جدول المحاضرات الدراسية:**\nيمكنك نشر جدول المحاضرات بصيغة PDF هنا ليتمكن جميع الطلاب من تحميله ومراجعته.")
    
    elif text == "❓ طرح سؤال":
        bot.reply_to(message, "❓ **طرح سؤال:**\nاكتب سؤالك أو استفسارك الآن في رسالة وسيقوم البوت بتسجيله وإرساله للمختصين.")
    
    elif text == "🔔 التذكيرات":
        bot.reply_to(message, "🔔 **قسم التذكيرات والتنبيهات:**\nتابع هنا أحدث المواعيد المهمة، الاختبارات، والتسليمات الخاصة بالمواد.")
    
    elif text == "📊 متابعة الأسئلة":
        bot.reply_to(message, "📊 **متابعة الأسئلة:**\nهنا يتم عرض وتتبع حالة الأسئلة والاستفسارات التي تم طرحها من قِبل الطلاب.")
    
    elif text == "👨‍💻 مطور البوت":
        bot.reply_to(message, "👨‍💻 **مطور النظام:**\nتم تطوير وتبرمجة هذا البوت بواسطة المهندس: **محمد الظاهر**.")
    
    else:
        # إذا كتب الطالب سؤالاً أو استفساراً عادياً، يتم الرد عليه وتنبيه الأدمن إن أمكن
        bot.reply_to(message, f"✅ تم استلام رسالتك يا مهندس بنجاح وسيتم التعامل معها.")

if __name__ == "__main__":
    keep_alive()
    print("Bot is starting...")
    bot.polling(none_stop=True)
