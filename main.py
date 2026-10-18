import os
import telebot
from flask import Flask
from threading import Thread

# 1. إعداد سيرفر Web للحفاظ على نشاط البوت على Render
app = Flask('')

@app.route('/')
def home():
    return "I am alive! IT Parallel Bot is running smoothly."

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. قراءة المتغيرات وإعادة تهيئة البوت
TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

bot = telebot.TeleBot(TOKEN)

# 3. قائمة الأوامر المتقدمة واللوحة الرئيسية
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_name = message.from_user.first_name
    welcome_text = (
        f"أهلاً بك يا مهندس {user_name} في بوت:\n"
        f"🎓 **تكنولوجيا المعلومات (IT) - موازي** 🎓\n\n"
        f"اختر من القائمة أدناه أو اكتب أمرك المباشر."
    )
    
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_materials = telebot.types.KeyboardButton("📚 المواد والخطط")
    btn_channels = telebot.types.KeyboardButton("📢 قنوات الدفعة")
    btn_info = telebot.types.KeyboardButton("ℹ️ معلومات الموازي")
    btn_contact = telebot.types.KeyboardButton("👨‍💼 التواصل مع الإدارة")
    
    markup.add(btn_materials, btn_channels, btn_info, btn_contact)
    bot.reply_to(message, welcome_text, parse_mode="Markdown", reply_markup=markup)

# 4. معالجة الرسائل
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text
    if text == "📚 المواد والخطط":
        bot.reply_to(message, "📂 **قسم المواد والخطط الدراسية:**\n• برمجة الحاسوب\n• معمارية وتصميم النظم\n• قواعد البيانات\n• شبكات الحاسوب")
    elif text == "📢 قنوات الدفعة":
        bot.reply_to(message, "🔗 **القنوات المعتمدة لدفعة تكنولوجيا المعلومات - موازي:**\n• القناة الرئيسية للإعلانات\n• مكتبة الملفات والملازم")
    elif text == "ℹ️ معلومات الموازي":
        bot.reply_to(message, "💡 **قسم تكنولوجيا المعلومات (IT) - النظام الموازي**")
    elif text == "👨‍💼 التواصل مع الإدارة":
        bot.reply_to(message, "📝 يمكنك إرسال استفسارك هنا مباشرة، وسيقوم مسؤول النظام بالرد عليك.")
    else:
        bot.reply_to(message, f"تم استلام رسالتك يا مهندس: '{text}'")

if __name__ == "__main__":
    keep_alive()
    print("Bot is starting...")
    bot.polling(none_stop=True)
  
