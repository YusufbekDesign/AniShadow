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
# --- 2-QISM BOSHLANISHI ---

# --- FOYDALANUVCHI INTERFEYSI VA QIDIRUV ---

@bot.message_handler(func=lambda m: m.text == "🔍 Anime qidirish")
def search_prompt(message):
    bot.send_message(message.chat.id, "🔢 Anime **kodini** yuboring (Masalan: 101):", 
                     parse_mode="Markdown", reply_markup=cancel_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔥 Top Animelar")
def show_top_animes(message):
    # Bu yerda bazadan eng ko'p ko'rilgan yoki oxirgi qo'shilganlarni chiqarish mumkin
    bot.send_message(message.chat.id, "🌟 Hozirda eng ommabop animelar ro'yxati shakllantirilmoqda...")

@bot.message_handler(func=lambda m: m.text == "💎 Premium obuna")
def premium_info(message):
    premium_text = (
        "💎 **AniShadow Premium afzalliklari:**\n\n"
        "✅ Barcha yopiq (Premium) animelarga kirish\n"
        "✅ Reklamasiz va cheklovlarsiz tomosha qilish\n"
        "✅ Yangi qismlarni birinchilardan bo'lib ko'rish\n\n"
        f"💳 Sotib olish uchun admin bilan bog'laning: {ADMIN_USER}"
    )
    bot.send_message(message.chat.id, premium_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🤝 Reklama")
def ads_info(message):
    bot.send_message(message.chat.id, f"🤝 Hamkorlik va reklama masalalari bo'yicha admin: {ADMIN_USER}")

@bot.message_handler(func=lambda m: m.text == "🏠 Asosiy Menyu")
def back_home(message):
    bot.send_message(message.chat.id, "🏠 Siz asosiy menyudasiz.", reply_markup=get_main_keyboard(message.from_user.id))

# --- ANIME QIDIRUV VA NATIJALAR ---

@bot.message_handler(func=lambda m: m.text and m.text.isdigit())
def search_anime_by_code(message):
    code = message.text
    anime = db.get_anime(code)
    uid = message.from_user.id

    if anime:
        # anime = (code, title, description, img_id, is_premium)
        title, is_prem_anime = anime[1], anime[4]
        
        # PREMIUM TEKSHIRUVI
        user_is_premium = db.is_premium(uid)
        
        if is_prem_anime and not user_is_premium and not is_admin(uid):
            lock_text = (
                f"🔒 **'{title}' — faqat Premium foydalanuvchilar uchun!**\n\n"
                "Ushbu animeni ko'rish uchun sizda Premium obuna bo'lishi kerak.\n"
                f"Murojaat: {ADMIN_USER}"
            )
            return bot.send_photo(message.chat.id, anime[3], caption=lock_text, parse_mode="Markdown")

        # Qismlarni (epizodlarni) olish
        episodes = db.get_episodes(code)
        
        markup = types.InlineKeyboardMarkup(row_width=4)
        btns = []
        for ep in episodes:
            # ep = (episode_number, file_id)
            btns.append(types.InlineKeyboardButton(f"{ep[0]}-qism", callback_data=f"play_{code}_{ep[0]}"))
        
        markup.add(*btns)
        
        status_tag = "💎 Premium" if is_prem_anime else "🟢 Bepul"
        caption = f"🎬 **Nomi:** {title}\n🌟 **Holati:** {status_tag}\n\n👇 Tomosha qilish uchun qismni tanlang:"
        
        bot.send_photo(message.chat.id, anime[3], caption=caption, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Afsuski, bunday kodli anime topilmadi. Iltimos, kodni tekshirib qayta yuboring.")

# --- VIDEO PLEYER (CALLBACK HANDLER) ---

@bot.callback_query_handler(func=lambda call: call.data.startswith("play_"))
def play_episode(call):
    # data format: play_code_num
    _, code, num = call.data.split("_")
    
    episodes = db.get_episodes(code)
    file_id = None
    for ep in episodes:
        if str(ep[0]) == num:
            file_id = ep[1]
            break
            
    if file_id:
        # Videoni yuborish
        bot.send_video(
            call.message.chat.id, 
            file_id, 
            caption=f"🎞 **{num}-qism**\n\n🤖 @AniShadowMythic — Maroqli hordiq!", 
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id, "Video yuklanmoqda...")
    else:
        bot.answer_callback_query(call.id, "❌ Video topilmadi.", show_alert=True)

# --- ADMIN: GLOBAL XABAR TARQATISH (BROADCAST) ---

@bot.message_handler(func=lambda m: m.text == "📢 Xabar Tarqatish" and is_admin(m.from_user.id))
def broadcast_start(message):
    user_states[message.from_user.id] = {'step': 'waiting_broadcast_text'}
    bot.send_message(message.chat.id, "📝 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing:", reply_markup=cancel_keyboard())

# Bu qism handling_admin_steps funksiyasiga qo'shimcha sifatida ishlaydi
# handle_admin_steps ichiga quyidagi shartni qo'shishingiz mumkin (yoki alohida yozish)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and user_states.get(m.from_user.id, {}).get('step') == 'waiting_broadcast_text')
def broadcast_finish(message):
    if message.text == "❌ Bekor qilish":
        del user_states[message.from_user.id]
        return bot.send_message(message.chat.id, "🚫 Bekor qilindi.", reply_markup=get_admin_keyboard())

    # Bazadan barcha foydalanuvchilarni olish (bu funksiyani Database ga qo'shish kerak)
    # Hozircha namunaviy mantiq:
    bot.send_message(message.chat.id, "🚀 Xabar tarqatish boshlandi...")
    # ... (bazadagi barcha user_id larni aylanish kodi) ...
    bot.send_message(message.chat.id, "✅ Xabar hamma foydalanuvchilarga yuborildi!")
    del user_states[message.from_user.id]

# --- 24/7 ISHLASH VA ERROR HANDLING ---

def run_bot():
    """Botni uzluksiz yurgizish funksiyasi"""
    print(f"🚀 AniShadow V11 ishga tushdi (Admin: {ADMIN_USER})")
    
    while True:
        try:
            # skip_pending=True eski o'qilmagan xabarlarni o'chirib yuboradi
            bot.infinity_polling(timeout=20, long_polling_timeout=10, skip_pending=True)
        except Exception as e:
            logging.error(f"⚠️ Botda xatolik yuz berdi: {e}")
            time.sleep(5) # 5 soniyadan keyin qayta harakat qiladi

if __name__ == "__main__":
    run_bot()

# --- 2-QISM TUGADI ---
# --- 3-QISM BOSHLANISHI ---

# --- ADMIN: STATISTIKA VA FOYDALANUVCHILARNI BOSHQARISH ---

@bot.message_handler(func=lambda m: m.text == "📈 Statistika" and is_admin(m.from_user.id))
def show_stats(message):
    """Bot statistikasini ko'rsatish"""
    conn = db.connection
    cursor = conn.cursor()
    
    # Jami foydalanuvchilar
    total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    # Premium foydalanuvchilar
    prem_users = cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1").fetchone()[0]
    # Jami animelar
    total_animes = cursor.execute("SELECT COUNT(*) FROM animes").fetchone()[0]
    
    stats_msg = (
        "📊 **AniShadow Global Statistikasi**\n\n"
        f"👤 Jami foydalanuvchilar: `{total_users}`\n"
        f"💎 Premium a'zolar: `{prem_users}`\n"
        f"🎬 Bazadagi animelar: `{total_animes}`\n\n"
        "⚡️ Server holati: `Online 24/7`"
    )
    bot.send_message(message.chat.id, stats_msg, parse_mode="Markdown")

# --- ADMIN: XABAR TARQATISH (TO'LIQ MANTIQ) ---

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and user_states.get(m.from_user.id, {}).get('step') == 'waiting_broadcast_text')
def handle_broadcast(message):
    if message.text == "❌ Bekor qilish":
        del user_states[message.from_user.id]
        return bot.send_message(message.chat.id, "🚫 Bekor qilindi.", reply_markup=get_admin_keyboard())

    broadcast_text = message.text
    cursor = db.connection.cursor()
    users = cursor.execute("SELECT user_id FROM users").fetchall()
    
    bot.send_message(message.chat.id, f"🚀 `{len(users)}` ta foydalanuvchiga yuborish boshlandi...", parse_mode="Markdown")
    
    count = 0
    for user in users:
        try:
            bot.send_message(user[0], broadcast_text)
            count += 1
            time.sleep(0.05) # Telegram spam filteriga tushmaslik uchun
        except Exception:
            continue
            
    bot.send_message(message.chat.id, f"✅ Xabar tarqatish yakunlandi!\nYetkazildi: `{count}` ta foydalanuvchiga.", parse_mode="Markdown")
    del user_states[message.from_user.id]

# --- FOYDALANUVCHI: HISOB MA'LUMOTLARI ---

@bot.message_handler(func=lambda m: m.text == "📊 Mening hisobim")
def my_account(message):
    uid = message.from_user.id
    status = "💎 Premium" if db.is_premium(uid) else "🟢 Oddiy foydalanuvchi"
    
    acc_text = (
        "👤 **Sizning ma'lumotlaringiz:**\n\n"
        f"🆔 ID: `{uid}`\n"
        f"🎭 Status: {status}\n"
        f"🤖 Bot: @AniShadowMythic"
    )
    bot.send_message(message.chat.id, acc_text, parse_mode="Markdown")

# --- XAVFSIZLIK: HAR QANDAY XATOLIKNI USHLASH ---

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_all_other_messages(message):
    """Noma'lum buyruqlarni chiroyli qaytarish"""
    if message.from_user.id in user_states:
        # Agar admin biror narsani yuklayotgan bo'lsa, xalaqit bermaymiz
        return
        
    bot.send_message(
        message.chat.id, 
        "❓ **Noma'lum buyruq.**\n\nIltimos, menyudan foydalaning yoki anime kodini yuboring.",
        reply_markup=get_main_keyboard(message.from_user.id),
        parse_mode="Markdown"
    )

# --- BOTNI QAYTA ISHGA TUSHIRISH MANTIQI (RELIABILITY) ---

def start_polling():
    """Bot o'chib qolmasligi uchun cheksiz sikl"""
    while True:
        try:
            logging.info("Bot polling rejimi faollashdi...")
            bot.polling(none_stop=True, interval=0, timeout=40)
        except Exception as e:
            logging.error(f"Xatolik: {e}. 10 soniyadan keyin qayta urunish...")
            time.sleep(10)

if __name__ == "__main__":
    start_polling()


