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
ADMIN_ID = os.environ.get('ADMIN_ID') # رقم الآيدي الخاص بك

bot = telebot.TeleBot(TOKEN)
user_states = {}
admin_upload_cache = {} # لحفظ الملف المؤقت الذي يرفعه الآدمن قبل اختيار المادة

# قاعدة بيانات ديناميكية لحفظ المحتويات التي يرفعها الآدمن
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
    
    # التحقق إذا كان المرسل هو الآدمن ويريد رفع محتوى جديد
    if ADMIN_ID and str(user_id) == str(ADMIN_ID):
        # إذا أرسل الآدمن ملفاً أو رسالة ولم يكن يكتب سؤالاً عادياً
        if message.content_type != 'text' or (message.text and not message.text.startswith('/') and user_states.get(user_id) != "waiting_for_question"):
            # حفظ المحتوى مؤقتاً في الذاكرة لتوجيهه
