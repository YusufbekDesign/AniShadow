import os
import time
import logging
from dotenv import load_dotenv
import telebot
from telebot import types
from database import Database

# .env faylidan ma'lumotlarni yuklaymiz
load_dotenv()

# --- KONFIGURATSIYA ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7878240647")) #
ADMIN_USER = "@Shadow_Mythic" #

# Bot va Baza obyektlarini yaratamiz
bot = telebot.TeleBot(BOT_TOKEN)
db = Database()

# Loglarni sozlash (Xatolarni terminalda ko'rish uchun)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Admin panel uchun vaqtinchalik xotira (State management)
user_states = {}

# --- YORDAMCHI FUNKSIYALAR ---

def is_admin(user_id):
    """Foydalanuvchi admin ekanligini tekshiradi"""
    return user_id == ADMIN_ID #

def get_main_keyboard(user_id):
    """Asosiy menyu tugmalari"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_search = types.KeyboardButton("🔍 Anime qidirish")
    btn_top = types.KeyboardButton("🔥 Top Animelar")
    btn_prem = types.KeyboardButton("💎 Premium obuna")
    btn_ads = types.KeyboardButton("🤝 Reklama")
    
    markup.add(btn_search, btn_top)
    markup.add(btn_prem, btn_ads)
    
    if is_admin(user_id):
        markup.add(types.KeyboardButton("⚙️ Admin Panel"))
    
    return markup

def get_admin_keyboard():
    """Admin panel uchun maxsus tugmalar"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➕ Oddiy Anime", "💎 Premium Anime")
    markup.add("🎬 Qism Qo'shish", "🌟 Premium Berish")
    markup.add("📢 Xabar Tarqatish", "📈 Statistika")
    markup.add("🏠 Asosiy Menyu")
    return markup

def cancel_keyboard():
    """Amalni bekor qilish tugmasi"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ Bekor qilish")
    return markup

# --- COMMAND HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    uname = message.from_user.username
    
    # Foydalanuvchini bazaga qo'shamiz
    db.add_user(uid, uname)
    
    welcome_text = (
        f"🎬 **AniShadow botiga xush kelibsiz!**\n\n" #
        f"Bu yerda siz eng sara animelarni HD sifatda topishingiz mumkin.\n"
        f"Anime kodini yozing yoki menyudan foydalaning."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

# --- ADMIN PANEL MANTIQI (ASOSIY QISM) ---

@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel" and is_admin(m.from_user.id))
def admin_panel_home(message):
    bot.send_message(message.chat.id, "🛠 **Admin boshqaruv markazi**", parse_mode="Markdown", reply_markup=get_admin_keyboard())

# 1. ANIME QO'SHISH BOSQICHLARI
@bot.message_handler(func=lambda m: m.text in ["➕ Oddiy Anime", "💎 Premium Anime"] and is_admin(m.from_user.id))
def add_anime_start(message):
    is_premium_anime = 1 if "Premium" in message.text else 0
    user_states[message.from_user.id] = {'step': 'waiting_anime_code', 'is_prem': is_premium_anime}
    
    bot.send_message(message.chat.id, "🔢 Anime uchun **unikal kod** kiriting (masalan: 101):", 
                     parse_mode="Markdown", reply_markup=cancel_keyboard())

# 2. QISM QO'SHISH BOSQICHLARI
@bot.message_handler(func=lambda m: m.text == "🎬 Qism Qo'shish" and is_admin(m.from_user.id))
def add_episode_start(message):
    user_states[message.from_user.id] = {'step': 'waiting_ep_anime_code'}
    bot.send_message(message.chat.id, "🔢 Qaysi animega qism qo'shmoqchisiz? Kodini yozing:", 
                     reply_markup=cancel_keyboard())

# 3. PREMIUM BERISH
@bot.message_handler(func=lambda m: m.text == "🌟 Premium Berish" and is_admin(m.from_user.id))
def give_premium_start(message):
    user_states[message.from_user.id] = {'step': 'waiting_user_id'}
    bot.send_message(message.chat.id, "👤 Foydalanuvchining **Telegram ID** raqamini yuboring:", 
                     parse_mode="Markdown", reply_markup=cancel_keyboard())

# --- ADMIN STEPS HANDLING (Harakatlarni nazorat qilish) ---

@bot.message_handler(func=lambda m: m.from_user.id in user_states)
def handle_admin_steps(message):
    uid = message.from_user.id
    state = user_states[uid]

    if message.text == "❌ Bekor qilish":
        del user_states[uid]
        return bot.send_message(message.chat.id, "🚫 Amal bekor qilindi.", reply_markup=admin_kb())

    # Anime qo'shish mantiqi
    if state['step'] == 'waiting_anime_code':
        state['code'] = message.text
        state['step'] = 'waiting_anime_title'
        bot.send_message(message.chat.id, "📝 Anime **nomini** kiriting:")

    elif state['step'] == 'waiting_anime_title':
        state['title'] = message.text
        state['step'] = 'waiting_anime_img'
        bot.send_message(message.chat.id, "🖼 Anime uchun **poster (Rasm)** yuboring:")

    elif state['step'] == 'waiting_anime_img':
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            db.add_anime(state['code'], state['title'], "", file_id, state['is_prem'])
            bot.send_message(message.chat.id, f"✅ Anime saqlandi!\nKod: {state['code']}\nNomi: {state['title']}", 
                             reply_markup=get_admin_keyboard())
            del user_states[uid]
        else:
            bot.send_message(message.chat.id, "❌ Iltimos, rasm yuboring!")

    # Epizod qo'shish mantiqi
    elif state['step'] == 'waiting_ep_anime_code':
        anime = db.get_anime(message.text)
        if anime:
            state['anime_code'] = message.text
            state['step'] = 'waiting_ep_video'
            bot.send_message(message.chat.id, f"🎬 **{anime[1]}** uchun video yuboring:")
        else:
            bot.send_message(message.chat.id, "❌ Bunday kodli anime topilmadi. Qayta urinib ko'ring:")

    elif state['step'] == 'waiting_ep_video':
        if message.content_type == 'video':
            # Avtomatik numeratsiya
            existing_eps = db.get_episodes(state['anime_code'])
            next_num = len(existing_eps) + 1
            db.add_episode(state['anime_code'], next_num, message.video.file_id)
            bot.send_message(message.chat.id, f"✅ {next_num}-qism saqlandi!", reply_markup=get_admin_keyboard())
            del user_states[uid]
        else:
            bot.send_message(message.chat.id, "❌ Iltimos, video fayl yuboring!")

    # Premium berish mantiqi
    elif state['step'] == 'waiting_user_id':
        try:
            target_id = int(message.text)
            db.set_premium(target_id, True)
            bot.send_message(message.chat.id, f"💎 ID: {target_id} ga Premium berildi!", reply_markup=get_admin_keyboard())
            bot.send_message(target_id, "🎉 Tabriklaymiz! Sizga **AniShadow Premium** taqdim etildi!")
            del user_states[uid]
        except ValueError:
            bot.send_message(message.chat.id, "❌ ID faqat raqamlardan iborat bo'lishi kerak!")

# --- 1-QISM TUGADI ---
# (Davomi kutilmoqda...)
