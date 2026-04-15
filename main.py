import telebot
import sqlite3
import datetime
import os
from telebot import types
from flask import Flask
from threading import Thread

# ==================== SOZLAMALAR ====================
# Tokenni environment variable dan olish (Railway yoki boshqa hostda sozlangan)
BOT_TOKEN = os.getenv('BOT_TOKEN', "8463516034:AAFCzKb7USbIDfG6Tm7LCHbK7NU8EoBQ8kM")  # agar env bo'lmasa, shu ishlaydi
ADMIN_ID = 7878240647
BOT_USERNAME = "Anishadowmythicbot"

# Zayavka kanalingiz ID-si va havolasi
KANAL_ID = -1002361622352
ZAYAVKA_LINK = "https://t.me/+O08QOzg7QSo1YzEy"

# Botni aniqlash
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# ==================== FOYDALANUVCHIGA XABAR YOZISH (/msg) ====================
@bot.message_handler(commands=['msg'])
def test_msg(message):
    # Admin ruxsatini tekshirish (Super Admin yoki ruxsati bor admin)
    perms = get_admin_perms(message.from_user.id)
    if message.from_user.id != ADMIN_ID and (not perms or not perms.get('write_user')):
        bot.reply_to(message, "⚠️ Sizda foydalanuvchilarga xabar yozish ruxsati yo'q.")
        return

    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "💡 Foydalanish: <code>/msg [ID] [xabar]</code>", parse_mode='HTML')
            return
        
        target_id = parts[1].strip()
        msg_text = parts[2]
        
        # ID raqam ekanligini tekshirish
        if not target_id.isdigit():
            bot.reply_to(message, "⚠️ Xato: Foydalanuvchi ID raqami faqat raqamlardan iborat bo'lishi kerak.")
            return

        bot.send_message(target_id, f"📩 <b>Adminstratsiyadan xabar:</b>\n\n{msg_text}", parse_mode='HTML')
        bot.reply_to(message, "✅ Xabar yuborildi!")
    except Exception as e:
        bot.reply_to(message, "❌ Xato: Foydalanuvchi botni bloklagan bo'lishi mumkin.")
        

# ==================== BAZA ====================
def get_db():
    conn = sqlite3.connect('anishadow_final.db', check_same_thread=False)
    return conn, conn.cursor()

def init_db():
    conn, cursor = get_db()

    # Asosiy jadvallar
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, status TEXT DEFAULT "free")')
    cursor.execute('CREATE TABLE IF NOT EXISTS animes (code TEXT PRIMARY KEY, title TEXT, photo_id TEXT, views INTEGER DEFAULT 0, is_premium INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS episodes (anime_code TEXT, ep_num INTEGER, video_id TEXT)')

    # Support limit jadvali
    cursor.execute('''CREATE TABLE IF NOT EXISTS support_limits
                     (user_id INTEGER PRIMARY KEY, last_reset TEXT, msg_count INTEGER DEFAULT 0)''')

    # Zayavkalar jadvali
    cursor.execute('CREATE TABLE IF NOT EXISTS requests (user_id INTEGER PRIMARY KEY)')

    # Adminlar jadvali
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        can_add_anime INTEGER DEFAULT 0,
        can_add_episode INTEGER DEFAULT 0,
        can_delete_anime INTEGER DEFAULT 0,
        can_delete_episode INTEGER DEFAULT 0,
        can_premium INTEGER DEFAULT 0,
        can_broadcast INTEGER DEFAULT 0,
        can_view_stats INTEGER DEFAULT 0,
        can_write_user INTEGER DEFAULT 0
    )''')

    # Foydalanuvchi progress jadvali (qaysi qism ko‘rilgan)
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_progress (
        user_id INTEGER,
        anime_code TEXT,
        last_episode INTEGER,
        PRIMARY KEY (user_id, anime_code)
    )''')

    # Super adminni bazaga qo'shish (agar mavjud bo'lmasa)
    cursor.execute('''INSERT OR IGNORE INTO admins (user_id, can_add_anime, can_add_episode, can_delete_anime,
                     can_delete_episode, can_premium, can_broadcast, can_view_stats, can_write_user)
                     VALUES (?, 1,1,1,1,1,1,1,1)''', (ADMIN_ID,))
    conn.commit()

init_db()

# ==================== YORDAMCHI FUNKSIYALAR ====================
def is_subscribed(user_id):
    return True  # Har doim ruxsat berish

def check_subscription(message):
    return True

def get_admin_perms(user_id):
    """Foydalanuvchining admin ruxsatlarini qaytaradi (lug'at)"""
    # Super admin (ADMIN_ID) uchun barcha ruxsatlar 1
    if user_id == ADMIN_ID:
        return {
            'add_anime': 1,
            'add_episode': 1,
            'delete_anime': 1,
            'delete_episode': 1,
            'premium': 1,
            'broadcast': 1,
            'view_stats': 1,
            'write_user': 1
        }
    conn, cursor = get_db()
    row = cursor.execute('''SELECT can_add_anime, can_add_episode, can_delete_anime,
                            can_delete_episode, can_premium, can_broadcast,
                            can_view_stats, can_write_user
                            FROM admins WHERE user_id = ?''', (user_id,)).fetchone()
    if not row:
        return None
    perms = {
        'add_anime': row[0],
        'add_episode': row[1],
        'delete_anime': row[2],
        'delete_episode': row[3],
        'premium': row[4],
        'broadcast': row[5],
        'view_stats': row[6],
        'write_user': row[7]
    }
    return perms

def is_admin(user_id):
    """Foydalanuvchi admin yoki super admin ekanligini tekshiradi"""
    if user_id == ADMIN_ID:
        return True
    conn, cursor = get_db()
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

def get_last_episode(user_id, anime_code):
    """Foydalanuvchining so‘nggi ko‘rgan qismini qaytaradi"""
    conn, cursor = get_db()
    cursor.execute("SELECT last_episode FROM user_progress WHERE user_id = ? AND anime_code = ?", (user_id, anime_code))
    row = cursor.fetchone()
    return row[0] if row else None

def update_last_episode(user_id, anime_code, ep_num):
    """Foydalanuvchining so‘nggi ko‘rgan qismini yangilaydi"""
    conn, cursor = get_db()
    cursor.execute("INSERT OR REPLACE INTO user_progress (user_id, anime_code, last_episode) VALUES (?, ?, ?)",
                   (user_id, anime_code, ep_num))
    conn.commit()

# ==================== ZAYAVKA AVTOMATIK TASDIQLASH ====================
@bot.chat_join_request_handler()
def handle_join_request(chat_join_request):
    u_id = chat_join_request.from_user.id
    conn, cursor = get_db()
    cursor.execute("INSERT OR IGNORE INTO requests (user_id) VALUES (?)", (u_id,))
    conn.commit()
    try:
        bot.approve_chat_join_request(KANAL_ID, u_id)
        print(f"✅ ZAYAVKA TASDIQLANDI: {u_id}")
    except Exception as e:
        print(f"❌ Xatolik: {e}")

# ==================== KLAVIATURALAR ====================
def main_kb(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔍 Anime izlash", "🔥 Top Animelar")
    kb.add("📚 Qo'llanma", "✍️ Adminga murojaat")
    kb.add("💵 Reklama va Homiy")
    if is_admin(user_id):
        kb.add("⚙️ Admin Panel")
    return kb

def admin_kb(user_id):
    perms = get_admin_perms(user_id)
    if perms is None:
        return types.ReplyKeyboardMarkup(resize_keyboard=True).add("🏠 Bosh menyu")
    
    # row_width=2 tugmalarni 2 tadan qilib taxlaydi
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = []
    
    if perms['add_anime']: buttons.append("➕ Anime yuklash")
    if perms['add_episode']: 
        buttons.append("🎬 Qism qo'shish")
        buttons.append("⚡️ Tezkor yuklash") # Yangi tugma
    if perms['view_stats']: buttons.append("📊 Statistika")
    if perms['broadcast']: buttons.append("📢 Reklama yuborish")
    if perms['delete_anime']: buttons.append("🗑 Anime o'chirish")
    if perms['delete_episode']: buttons.append("🎬 Qismni o'chirish")
    if perms['premium']: buttons.append("💎 Premium Sozlamalari")
    if perms['write_user']: buttons.append("📩 Foydalanuvchiga yozish")
    
    # Mana shu joyi barcha tugmalarni 2 tadan qilib qo'shadi
    kb.add(*buttons) 
    
    if user_id == ADMIN_ID:
        kb.row("👥 Admin boshqaruvi")
    
    kb.row("🏠 Bosh menyu")
    return kb
    
    

def cancel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🚫 Bekor qilish")
    return kb

# ==================== TEKSHIRISH CALLBACK ====================
@bot.callback_query_handler(func=lambda call: call.data == "check_subs")
def check_subscription_callback(call):
    if is_subscribed(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ Kanalga a'zoligingiz tasdiqlandi! Endi botdan foydalanishingiz mumkin.", reply_markup=main_kb(call.from_user.id))
    else:
        bot.answer_callback_query(call.id, "Hali kanalga qo'shilmagansiz. Iltimos, avval so'rov yuboring.", show_alert=True)

# ==================== BOSHQA MENYU TUGMALARI ====================
@bot.message_handler(func=lambda m: m.text == "💵 Reklama va Homiy")
def ad_sponsor(message):
    text = f"🤝 <b>Reklama va Homiylik masalalari bo'yicha:</b>\n\nIltimos, to'g'ridan-to'g'ri adminga yozing:"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 Adminga yozish", url=f"tg://user?id={ADMIN_ID}"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📚 Qo'llanma")
def guide(message):
    if not check_subscription(message):
        return
    text = """📚 <b>Botdan foydalanish qo'llanmasi:</b>

1️⃣ <b>Anime qidirish:</b> Kanalimizdan ko'rmoqchi bo'lgan animengiz kodini toping (Masalan: 101).
2️⃣ <b>Kodni yozish:</b> Botga o'sha raqamni yuboring.
3️⃣ <b>Qismlarni ko'rish:</b> Anime kelib chiqqandan so'ng, rasm ostidagi raqamlarni (1, 2, 3...) bossangiz, o'sha qism videosi keladi.

<i>Agar biror muammo bo'lsa, "Reklama va Homiy" bo'limi orqali adminga yozishingiz mumkin.</i>"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "🔍 Anime izlash")
def search_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔢 Kod orqali", callback_data="search_code"),
        types.InlineKeyboardButton("📝 Nomi orqali", callback_data="search_name")
    )
    markup.add(types.InlineKeyboardButton("🎭 Janrlar", callback_data="search_genre"))
    markup.add(
        types.InlineKeyboardButton("🆕 Yangi yuklanganlar", callback_data="search_new"),
        types.InlineKeyboardButton("🔥 Top animelar", callback_data="search_top")
    )
    bot.send_message(message.chat.id, "👇 Qidiruv turini tanlang:", reply_markup=markup)

# Nomi orqali qidirish natijasi
def process_search_name(message):
    search_text = message.text.strip()
    conn, cursor = get_db()
    cursor.execute("SELECT code, title FROM animes WHERE title LIKE ?", (f"%{search_text}%",))
    results = cursor.fetchall()
    conn.close()
    
    if results:
        text = f"🔍 <b>\"{search_text}\"</b> nomi bo'yicha topilgan animelar:\n\n"
        for r in results:
            text += f"🎬 <b>{r[1]}</b> — Kod: <code>{r[0]}</code>\n"
        text += "\n<i>Ko'rmoqchi bo'lgan anime kodini yuboring!</i>"
        bot.send_message(message.chat.id, text, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, f"❌ <b>\"{search_text}\"</b> nomli anime topilmadi.")

@bot.message_handler(func=lambda m: m.text == "🏠 Bosh menyu")
def back_home(message):
    bot.send_message(message.chat.id, "Bosh menyuga qaytdik.", reply_markup=main_kb(message.from_user.id))

# ==================== START ====================
@bot.message_handler(commands=['start'])
def welcome(message):
    conn, cursor = get_db()
    u_id = message.from_user.id
    u_name = message.from_user.username if message.from_user.username else "yo'q"
    cursor.execute("INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)", (u_id, u_name))
    conn.commit()
    args = message.text.split()
    if len(args) > 1:
        anime_code = args[1]
        show_anime_by_code(message, anime_code)
        return
    text = f"""👋 <b>Assalomu alaykum, {message.from_user.first_name}!</b>

Men siz qidirayotgan barcha Animelarni topishga yordam beraman. Buning uchun Anime kodini aniq yozishingiz kerak!

☝️ <b>Masalan:</b> 1 yoki 101
📢 <b>Kanalimiz:</b> @AniShadowMythic

✅ <i>Tushungan bo'lsangiz, Anime kodini yuboring!</i>"""
    bot.send_message(message.chat.id, text, reply_markup=main_kb(u_id))

        


# ==================== ADMIN PANEL ====================
@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel" and is_admin(m.from_user.id))
def open_admin(message):
    bot.send_message(message.chat.id, "👨‍💻 Admin panelga xush kelibsiz:", reply_markup=admin_kb(message.from_user.id))

# ==================== ADMIN BOSHQARUVI (faqat super admin) ====================
add_temp = {}
edit_temp = {}

@bot.message_handler(func=lambda m: m.text == "👥 Admin boshqaruvi" and m.from_user.id == ADMIN_ID)
def manage_admins(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ Admin qo'shish", callback_data="add_admin"))
    markup.add(types.InlineKeyboardButton("📋 Adminlar ro'yxati", callback_data="list_admins"))
    bot.send_message(message.chat.id, "👥 Admin boshqaruvi:", reply_markup=markup)

# -------------------- Admin qo'shish (toggle bilan) --------------------
@bot.callback_query_handler(func=lambda call: call.data == "add_admin" and call.from_user.id == ADMIN_ID)
def add_admin_start(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, "➕ Admin qilmoqchi bo‘lgan foydalanuvchining ID raqamini yuboring:")
    bot.register_next_step_handler(msg, add_admin_get_id)

def add_admin_get_id(message):
    try:
        target_id = int(message.text)
    except:
        return bot.send_message(message.chat.id, "❌ Noto‘g‘ri ID. Bekor qilindi.", reply_markup=admin_kb(ADMIN_ID))
    # Vaqtinchalik ma'lumotlarni saqlash
    add_temp[target_id] = {
        'add_anime': 0,
        'add_episode': 0,
        'delete_anime': 0,
        'delete_episode': 0,
        'premium': 0,
        'broadcast': 0,
        'view_stats': 0,
        'write_user': 0
    }
    show_add_perms(message.chat.id, target_id)

def show_add_perms(chat_id, target_id, message_id=None):
    perms = add_temp[target_id]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"{'✅' if perms['add_anime'] else '❌'} Anime yuklash", callback_data=f"add_toggle_add_anime_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['add_episode'] else '❌'} Qism qo'shish", callback_data=f"add_toggle_add_episode_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['delete_anime'] else '❌'} Anime o'chirish", callback_data=f"add_toggle_delete_anime_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['delete_episode'] else '❌'} Qism o'chirish", callback_data=f"add_toggle_delete_episode_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['premium'] else '❌'} Premium", callback_data=f"add_toggle_premium_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['broadcast'] else '❌'} Reklama", callback_data=f"add_toggle_broadcast_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['view_stats'] else '❌'} Statistika", callback_data=f"add_toggle_view_stats_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['write_user'] else '❌'} Foydalanuvchiga yozish", callback_data=f"add_toggle_write_user_{target_id}"),
        types.InlineKeyboardButton("💾 Saqlash", callback_data=f"add_save_{target_id}"),
        types.InlineKeyboardButton("🚫 Bekor qilish", callback_data="add_cancel")
    )
    if message_id:
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, f"👤 ID: {target_id} uchun ruxsatlarni belgilang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_toggle_') and call.from_user.id == ADMIN_ID)
def add_toggle_callback(call):
    parts = call.data.split('_')
    target_id = int(parts[-1])
    perm_key = "_".join(parts[2:-1])

    if target_id in add_temp:
        # ✅ ni ❌ ga, ❌ ni ✅ ga o'zgartiradi
        add_temp[target_id][perm_key] = 1 - add_temp[target_id][perm_key]
        bot.answer_callback_query(call.id, "O'zgartirildi")
        # Menyu qayta chiziladi
        show_add_perms(call.message.chat.id, target_id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "Xatolik! Sessiya muddati o'tgan.", show_alert=True)
        # Tugma matnini yangilash
        perms = add_temp[target_id]
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton(f"{'✅' if perms['add_anime'] else '❌'} Anime yuklash", callback_data=f"add_toggle_add_anime_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['add_episode'] else '❌'} Qism qo'shish", callback_data=f"add_toggle_add_episode_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['delete_anime'] else '❌'} Anime o'chirish", callback_data=f"add_toggle_delete_anime_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['delete_episode'] else '❌'} Qism o'chirish", callback_data=f"add_toggle_delete_episode_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['premium'] else '❌'} Premium", callback_data=f"add_toggle_premium_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['broadcast'] else '❌'} Reklama", callback_data=f"add_toggle_broadcast_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['view_stats'] else '❌'} Statistika", callback_data=f"add_toggle_view_stats_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['write_user'] else '❌'} Foydalanuvchiga yozish", callback_data=f"add_toggle_write_user_{target_id}"),
            types.InlineKeyboardButton("💾 Saqlash", callback_data=f"add_save_{target_id}"),
            types.InlineKeyboardButton("🚫 Bekor qilish", callback_data="add_cancel")
        )
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
  

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_save_') and call.from_user.id == ADMIN_ID)
def add_save_callback(call):
    target_id = int(call.data.split('_')[2])
    if target_id not in add_temp:
        return bot.answer_callback_query(call.id, "Xatolik")
    perms = add_temp.pop(target_id)
    conn, cursor = get_db()
    cursor.execute('''INSERT OR REPLACE INTO admins (user_id, can_add_anime, can_add_episode,
                     can_delete_anime, can_delete_episode, can_premium, can_broadcast,
                     can_view_stats, can_write_user)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                   (target_id, perms['add_anime'], perms['add_episode'],
                    perms['delete_anime'], perms['delete_episode'], perms['premium'],
                    perms['broadcast'], perms['view_stats'], perms['write_user']))
    conn.commit()
    bot.edit_message_text(f"✅ Admin (ID: {target_id}) muvaffaqiyatli qo‘shildi!", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "add_cancel" and call.from_user.id == ADMIN_ID)
def add_cancel_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Bekor qilindi.", reply_markup=admin_kb(ADMIN_ID))
    bot.answer_callback_query(call.id)

# -------------------- Adminlar ro'yxati va tahrirlash --------------------
@bot.callback_query_handler(func=lambda call: call.data == "list_admins" and call.from_user.id == ADMIN_ID)
def list_admins(call):
    send_admin_list_page(call.message.chat.id, 0, call.message.message_id)

def send_admin_list_page(chat_id, offset, message_id=None):
    conn, cursor = get_db()
    admins = cursor.execute('''SELECT user_id, can_add_anime, can_add_episode, can_delete_anime,
                                can_delete_episode, can_premium, can_broadcast,
                                can_view_stats, can_write_user
                                FROM admins ORDER BY user_id LIMIT 5 OFFSET ?''', (offset,)).fetchall()
    total = cursor.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
    if not admins:
        text = "👥 Adminlar yo‘q."
        markup = None
    else:
        text = "👥 Adminlar ro‘yxati:\n\n"
        markup = types.InlineKeyboardMarkup(row_width=2)
        for a in admins:
            uid = a[0]
            perms = []
            if a[1]: perms.append("➕")
            if a[2]: perms.append("🎬")
            if a[3]: perms.append("🗑")
            if a[4]: perms.append("🎬🗑")
            if a[5]: perms.append("💎")
            if a[6]: perms.append("📢")
            if a[7]: perms.append("📊")
            if a[8]: perms.append("📩")
            perm_str = " ".join(perms) if perms else "❌"
            text += f"👤 ID: <code>{uid}</code>   Ruxsatlar: {perm_str}\n"
            markup.add(
                types.InlineKeyboardButton(f"✏️ Tahrirlash", callback_data=f"edit_admin_{uid}"),
                types.InlineKeyboardButton(f"🗑 O‘chirish", callback_data=f"del_admin_{uid}")
            )
        nav_btns = []
        if offset > 0:
            nav_btns.append(types.InlineKeyboardButton("⬅️ Orqaga", callback_data=f"admin_page_{offset-5}"))
        if offset + 5 < total:
            nav_btns.append(types.InlineKeyboardButton("Keyingisi ➡️", callback_data=f"admin_page_{offset+5}"))
        if nav_btns:
            markup.row(*nav_btns)
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_page_') and call.from_user.id == ADMIN_ID)
def admin_page_callback(call):
    offset = int(call.data.split('_')[2])
    send_admin_list_page(call.message.chat.id, offset, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_admin_') and call.from_user.id == ADMIN_ID)
def delete_admin(call):
    target_id = int(call.data.split('_')[2])
    if target_id == ADMIN_ID:
        return bot.answer_callback_query(call.id, "O‘zingizni o‘chira olmaysiz!", show_alert=True)
    conn, cursor = get_db()
    cursor.execute("DELETE FROM admins WHERE user_id = ?", (target_id,))
    conn.commit()
    bot.answer_callback_query(call.id, f"Admin (ID: {target_id}) o‘chirildi!")
    send_admin_list_page(call.message.chat.id, 0, call.message.message_id)

# Tahrirlash uchun vaqtinchalik ma'lumotlar
edit_temp = {}

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_admin_') and call.from_user.id == ADMIN_ID)
def edit_admin_start(call):
    target_id = int(call.data.split('_')[2])
    conn, cursor = get_db()
    row = cursor.execute('''SELECT can_add_anime, can_add_episode, can_delete_anime,
                            can_delete_episode, can_premium, can_broadcast,
                            can_view_stats, can_write_user
                            FROM admins WHERE user_id = ?''', (target_id,)).fetchone()
    if not row:
        return bot.answer_callback_query(call.id, "Admin topilmadi!", show_alert=True)
    edit_temp[target_id] = {
        'add_anime': row[0],
        'add_episode': row[1],
        'delete_anime': row[2],
        'delete_episode': row[3],
        'premium': row[4],
        'broadcast': row[5],
        'view_stats': row[6],
        'write_user': row[7]
    }
    show_edit_perms(call.message.chat.id, target_id, call.message.message_id)
def show_edit_perms(chat_id, target_id, message_id):
    perms = edit_temp[target_id]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"{'✅' if perms['add_anime'] else '❌'} Anime yuklash", callback_data=f"edit_toggle_add_anime_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['add_episode'] else '❌'} Qism qo'shish", callback_data=f"edit_toggle_add_episode_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['delete_anime'] else '❌'} Anime o'chirish", callback_data=f"edit_toggle_delete_anime_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['delete_episode'] else '❌'} Qism o'chirish", callback_data=f"edit_toggle_delete_episode_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['premium'] else '❌'} Premium", callback_data=f"edit_toggle_premium_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['broadcast'] else '❌'} Reklama", callback_data=f"edit_toggle_broadcast_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['view_stats'] else '❌'} Statistika", callback_data=f"edit_toggle_view_stats_{target_id}"),
        types.InlineKeyboardButton(f"{'✅' if perms['write_user'] else '❌'} Foydalanuvchiga yozish", callback_data=f"edit_toggle_write_user_{target_id}"),
        types.InlineKeyboardButton("💾 Saqlash", callback_data=f"edit_save_{target_id}"),
        types.InlineKeyboardButton("🚫 Bekor qilish", callback_data="edit_cancel")
    )
    bot.edit_message_text(f"✏️ ID: {target_id} ruxsatlarini tahrirlang:", chat_id, message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_toggle_') and call.from_user.id == ADMIN_ID)
def edit_toggle_callback(call):
    parts = call.data.split('_')
    target_id = int(parts[-1])
    perm_key = "_".join(parts[2:-1]) 

    if target_id in edit_temp:
        edit_temp[target_id][perm_key] = 1 - edit_temp[target_id][perm_key]
        bot.answer_callback_query(call.id, "O'zgartirildi")
        show_edit_perms(call.message.chat.id, target_id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "Sessiya tugagan. Qaytadan urinib ko'ring.", show_alert=True)
        # Tugmalarni yangilash
        perms = edit_temp[target_id]
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton(f"{'✅' if perms['add_anime'] else '❌'} Anime yuklash", callback_data=f"edit_toggle_add_anime_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['add_episode'] else '❌'} Qism qo'shish", callback_data=f"edit_toggle_add_episode_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['delete_anime'] else '❌'} Anime o'chirish", callback_data=f"edit_toggle_delete_anime_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['delete_episode'] else '❌'} Qism o'chirish", callback_data=f"edit_toggle_delete_episode_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['premium'] else '❌'} Premium", callback_data=f"edit_toggle_premium_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['broadcast'] else '❌'} Reklama", callback_data=f"edit_toggle_broadcast_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['view_stats'] else '❌'} Statistika", callback_data=f"edit_toggle_view_stats_{target_id}"),
            types.InlineKeyboardButton(f"{'✅' if perms['write_user'] else '❌'} Foydalanuvchiga yozish", callback_data=f"edit_toggle_write_user_{target_id}"),
            types.InlineKeyboardButton("💾 Saqlash", callback_data=f"edit_save_{target_id}"),
            types.InlineKeyboardButton("🚫 Bekor qilish", callback_data="edit_cancel")
        )
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_save_') and call.from_user.id == ADMIN_ID)
def edit_save_callback(call):
    target_id = int(call.data.split('_')[2])
    if target_id not in edit_temp:
        return bot.answer_callback_query(call.id, "Xatolik")
    perms = edit_temp.pop(target_id)
    conn, cursor = get_db()
    cursor.execute('''INSERT OR REPLACE INTO admins (user_id, can_add_anime, can_add_episode,
                     can_delete_anime, can_delete_episode, can_premium, can_broadcast,
                     can_view_stats, can_write_user)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                   (target_id, perms['add_anime'], perms['add_episode'],
                    perms['delete_anime'], perms['delete_episode'], perms['premium'],
                    perms['broadcast'], perms['view_stats'], perms['write_user']))
    conn.commit()
    bot.edit_message_text(f"✅ Admin (ID: {target_id}) tahrirlandi!", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)
    # Ro‘yxatga qaytish
    send_admin_list_page(call.message.chat.id, 0, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "edit_cancel" and call.from_user.id == ADMIN_ID)
def edit_cancel_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_admin_list_page(call.message.chat.id, 0, call.message.message_id)
    bot.answer_callback_query(call.id)

# Vaqtinchalik ma'lumotlar uchun global o‘zgaruvchilar
add_temp = {}   # admin qo'shish uchun

# ==================== ADMIN FUNKSIYALARI (ruxsat asosida) ====================
# Statistika
@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def show_stats(message):
    perms = get_admin_perms(message.from_user.id)
    if not perms or not perms['view_stats']:
        return
    conn, cursor = get_db()
    total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_animes = cursor.execute("SELECT COUNT(*) FROM animes").fetchone()[0]
    last_users = cursor.execute("SELECT user_id, username FROM users ORDER BY rowid DESC LIMIT 10").fetchall()
    u_text = ""
   for u in last_users:
        user_link = f'<a href="tg://user?id={u[0]}">{u[0]}</a>'
        # Faqat ID raqamini havola qilib chiqaramiz, username shart emas
        u_text += f"👤 ID: {user_link}\n"
    top_animes = cursor.execute("SELECT title, views FROM animes ORDER BY views DESC LIMIT 5").fetchall()
    a_text = ""
    for a in top_animes:
        a_text += f"🎬 {a[0]} — {a[1]} marta\n"
    text = f"📊 <b>Bot Statistikasi</b>\n\n" \
           f"👥 Jami foydalanuvchilar: {total_users}\n" \
           f"🎬 Jami animelar: {total_animes}\n\n" \
           f"🔝 <b>Eng ko'p ko'rilganlar:</b>\n{a_text if a_text else 'Hali ko`rilmagan'}\n\n" \
           f"🆕 <b>Oxirgi kirganlar (ID ustiga bosing):</b>\n{u_text}"
    bot.send_message(message.chat.id, text, parse_mode='HTML')

# Reklama yuborish
@bot.message_handler(func=lambda m: m.text == "📢 Reklama yuborish")
def start_broadcast(message):
    perms = get_admin_perms(message.from_user.id)
    if not perms or not perms['broadcast']:
        return
    msg = bot.send_message(message.chat.id, "📢 <b>Reklama xabarini yuboring:</b>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    conn, cursor = get_db()
    users = cursor.execute("SELECT user_id FROM users").fetchall()
    count = 0
    bot.send_message(message.chat.id, "🚀 Reklama tarqatilmoqda...")
    for user in users:
        try:
            bot.copy_message(user[0], message.chat.id, message.message_id)
            count += 1
        except:
            continue
    bot.send_message(message.chat.id, f"✅ Reklama {count} kishiga yuborildi!", reply_markup=admin_kb(message.from_user.id))

# Anime yuklash (ruxsat va super admin xabari)
@bot.message_handler(func=lambda m: m.text == "➕ Anime yuklash")
def add_step_1(message):
    perms = get_admin_perms(message.from_user.id)
    print(f"DEBUG: user={message.from_user.id}, perms={perms}")   # terminalda chiqadi
    if not perms or not perms['add_anime']:
        print("DEBUG: ruxsat yo‘q, funksiya to‘xtadi")
        return
    msg = bot.send_message(message.chat.id, "<b>1. Anime uchun POSTER (rasm) yuboring:</b>", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, add_step_2)

def add_step_2(message):
    if message.text == "🚫 Bekor qilish":
        return bot.send_message(message.chat.id, "❌ Yuklash bekor qilindi.", reply_markup=admin_kb(message.from_user.id))
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ Faqat rasm yuboring! Yoki jarayonni bekor qiling:", reply_markup=cancel_kb())
        bot.register_next_step_handler(msg, add_step_2)
        return
    photo_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "<b>2. Anime uchun KOD kiriting (Masalan: 101):</b>", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, add_step_3, photo_id)

def add_step_3(message, photo_id):
    if message.text == "🚫 Bekor qilish":
        return bot.send_message(message.chat.id, "❌ Yuklash bekor qilindi.", reply_markup=admin_kb(message.from_user.id))
    code = message.text
    msg = bot.send_message(message.chat.id, "<b>3. Anime NOMINI kiriting:</b>", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, add_step_final, photo_id, code)

def add_step_final(message, photo_id, code):
    if message.text == "🚫 Bekor qilish":
        return bot.send_message(message.chat.id, "❌ Yuklash bekor qilindi.", reply_markup=admin_kb(message.from_user.id))
    
    title = message.text
    conn, cursor = get_db()
    
    # Dublikat tekshiruvi
    cursor.execute("SELECT title FROM animes WHERE code = ?", (code,))
    exists = cursor.fetchone()
    if exists:
        conn.close()
        return bot.send_message(message.chat.id, f"❌ Xato! <b>{code}</b> kodi bazada bor: \"{exists[0]}\"\nBoshqa kod tanlang.", reply_markup=admin_kb(message.from_user.id))

    # Bazaga saqlash
    cursor.execute("INSERT INTO animes (code, title, photo_id) VALUES (?, ?, ?)", (code, title, photo_id))
    conn.commit()
    conn.close()

    # Super adminga xabar yuborish qismi (680-qatorlar atrofi)
    msg_to_admin = f"➕ <b>Yangi anime qo'shildi!</b>\n\n<b>Yukladi:</b> {message.from_user.first_name}\n<b>Nomi:</b> {title}\n<b>Kodi:</b> {code}"
    bot.send_message(ADMIN_ID, msg_to_admin, parse_mode='HTML')
    
    # Yuklagan adminga javob
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    res_text = f"✅ <b>Anime saqlandi!</b>\n\n🎬 Nomi: {title}\n📌 Kodi: {code}\n🔗 Havola: <code>{link}</code>"
    bot.send_message(message.chat.id, res_text, reply_markup=admin_kb(message.from_user.id))

# Qism qo'shish (ruxsat va super admin xabari)
@bot.message_handler(func=lambda m: m.text == "🎬 Qism qo'shish")
def ep_step_1(message):
    perms = get_admin_perms(message.from_user.id)
    if not perms or not perms['add_episode']:
        return
    conn, cursor = get_db()
    animes = cursor.execute("SELECT code, title FROM animes").fetchall()
    if not animes:
        return bot.send_message(message.chat.id, "❌ Hali bazaga hech qanday anime qo'shilmagan!")
    markup = types.InlineKeyboardMarkup(row_width=1)
    for a in animes:
        markup.add(types.InlineKeyboardButton(f"🎬 {a[1]} (Kod: {a[0]})", callback_data=f"addep_{a[0]}"))
    bot.send_message(message.chat.id, "<b>Qaysi animega qism qo'shamiz? Quyidagi ro'yxatdan tanlang:</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('addep_'))
def ep_step_2(call):
    code = call.data.split('_')[1]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id,
                           f"✅ Anime tanlandi (Kod: {code}).\n\n<b>Endi nechanchi qism ekanligini yozing (Masalan: 1):</b>",
                           reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, ep_step_3, code)

def ep_step_3(message, code):
    if message.text == "🚫 Bekor qilish":
        return bot.send_message(message.chat.id, "❌ Qism qo'shish bekor qilindi.", reply_markup=admin_kb(message.from_user.id))
    num = message.text
    if not num.isdigit():
        msg = bot.send_message(message.chat.id, "❌ Iltimos, faqat RAQAM yozing! (Yoki bekor qiling):", reply_markup=cancel_kb())
        bot.register_next_step_handler(msg, ep_step_3, code)
        return
    msg = bot.send_message(message.chat.id, f"<b>{num}-qism VIDEOSINI yuboring:</b>", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, ep_step_final, code, num)

def ep_step_final(message, code, num):
    if message.text == "🚫 Bekor qilish":
        return bot.send_message(message.chat.id, "❌ Qism qo'shish bekor qilindi.", reply_markup=admin_kb(message.from_user.id))
    
    if message.content_type != 'video':
        msg = bot.send_message(message.chat.id, "❌ Faqat video yuboring! (Yoki bekor qiling):", reply_markup=cancel_kb())
        bot.register_next_step_handler(msg, ep_step_final, code, num)
        return

    conn, cursor = get_db()
    
    # --- QISM DUBLIKATINI TEKSHIRISH ---
    cursor.execute("SELECT 1 FROM episodes WHERE anime_code = ? AND ep_num = ?", (code, int(num)))
    if cursor.fetchone():
        conn.close()
        return bot.send_message(message.chat.id, f"❌ Bu animeda {num}-qism allaqachon bor!", reply_markup=admin_kb(message.from_user.id))
    # ----------------------------------

    # Sizning eski INSERT qatoringiz:
    cursor.execute("INSERT INTO episodes VALUES (?, ?, ?)", (code, int(num), message.video.file_id))
    conn.commit()
    # Pastdagi Super admin xabarlari qolsin
    # Super adminga xabar
    bot.send_message(ADMIN_ID, f"🎬 <b>Yangi qism qo'shildi!</b>\n\n<b>Yukladi:</b> {message.from_user.first_name} (ID: {message.from_user.id})\n<b>Anime kodi:</b> {code}\n<b>Qism:</b> {num}", parse_mode='HTML')
    bot.send_message(message.chat.id, f"✅ <b>{code}</b>-anime uchun <b>{num}</b>-qism muvaffaqiyatli saqlandi!", reply_markup=admin_kb(message.from_user.id))

# Anime o'chirish (ruxsat)
@bot.message_handler(func=lambda m: m.text == "🗑 Anime o'chirish")
def delete_anime_list(message):
    perms = get_admin_perms(message.from_user.id)
    if not perms or not perms['delete_anime']:
        return
    conn, cursor = get_db()
    animes = cursor.execute("SELECT code, title FROM animes").fetchall()
    if not animes:
        return bot.send_message(message.chat.id, "❌ Bazada o'chirish uchun anime yo'q.")
    markup = types.InlineKeyboardMarkup(row_width=1)
    for a in animes:
        markup.add(types.InlineKeyboardButton(f"❌ {a[1]} (Kod: {a[0]})", callback_data=f"del_{a[0]}"))
    bot.send_message(message.chat.id, "🗑 Qaysi animeni o'chirmoqchisiz?", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def delete_anime_final(call):
    perms = get_admin_perms(call.from_user.id)
    if not perms or not perms['delete_anime']:
        return bot.answer_callback_query(call.id, "Sizda bu ruxsat yo'q!", show_alert=True)
    anime_code = call.data.split('_')[1]
    conn, cursor = get_db()
    cursor.execute("DELETE FROM animes WHERE code = ?", (anime_code,))
    cursor.execute("DELETE FROM episodes WHERE anime_code = ?", (anime_code,))
    conn.commit()
    bot.answer_callback_query(call.id, "O'chirildi!")
    bot.edit_message_text(f"✅ Kod: {anime_code} bazadan o'chirildi.", call.message.chat.id, call.message.message_id)

# Qismni o'chirish (ruxsat)
@bot.message_handler(func=lambda m: m.text == "🎬 Qismni o'chirish")
def delete_ep_start(message):
    perms = get_admin_perms(message.from_user.id)
    if not perms or not perms['delete_episode']:
        return
    conn, cursor = get_db()
    animes = cursor.execute("SELECT code, title FROM animes").fetchall()
    if not animes:
        return bot.send_message(message.chat.id, "❌ Bazada birorta ham anime yo'q.")
    markup = types.InlineKeyboardMarkup(row_width=1)
    for a in animes:
        markup.add(types.InlineKeyboardButton(f"🎬 {a[1]}", callback_data=f"epdel_list_{a[0]}"))
    bot.send_message(message.chat.id, "<b>Qaysi animening qismini o'chirmoqchisiz?</b>", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('epdel_list_'))
def delete_ep_select(call):
    perms = get_admin_perms(call.from_user.id)
    if not perms or not perms['delete_episode']:
        return bot.answer_callback_query(call.id, "Sizda bu ruxsat yo'q!", show_alert=True)
    anime_code = call.data.split('_')[2]
    conn, cursor = get_db()
    eps = cursor.execute("SELECT ep_num FROM episodes WHERE anime_code = ? ORDER BY ep_num ASC", (anime_code,)).fetchall()
    if not eps:
        return bot.answer_callback_query(call.id, "Bu animeda hali qismlar yo'q!", show_alert=True)
    markup = types.InlineKeyboardMarkup(row_width=5)
    btns = []
    for e in eps:
        btns.append(types.InlineKeyboardButton(f"{e[0]}", callback_data=f"epdel_exec_{anime_code}_{e[0]}"))
    markup.add(*btns)
    markup.add(types.InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_del_anime"))
    bot.edit_message_text(f"🔢 <b>Kod: {anime_code}</b>\n\nO'chirmoqchi bo'lgan qismingizni tanlang:",
                          call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('epdel_exec_'))
def delete_ep_final(call):
    perms = get_admin_perms(call.from_user.id)
    if not perms or not perms['delete_episode']:
        return bot.answer_callback_query(call.id, "Sizda bu ruxsat yo'q!", show_alert=True)
    data = call.data.split('_')
    anime_code = data[2]
    ep_num = data[3]
    conn, cursor = get_db()
    cursor.execute("DELETE FROM episodes WHERE anime_code = ? AND ep_num = ?", (anime_code, ep_num))
    conn.commit()
    bot.answer_callback_query(call.id, f"{ep_num}-qism o'chirildi!", show_alert=True)
    delete_ep_select(call)  # qayta ro'yxatni ko'rsatish

@bot.callback_query_handler(func=lambda call: call.data == "back_to_del_anime")
def back_to_del_anime(call):
    delete_ep_start(call.message)

# ==================== ANIME KO'RSATISH VA TOP ====================
def show_anime_by_code(message, code):
    if not check_subscription(message):
        return
    user_id = message.from_user.id
    conn, cursor = get_db()
    cursor.execute("UPDATE animes SET views = views + 1 WHERE code = ?", (code,))
    conn.commit()
    anime = cursor.execute("SELECT code, title, photo_id, views FROM animes WHERE code = ?", (code,)).fetchone()
    if anime:
        a_code, title, photo, views = anime
        eps = cursor.execute("SELECT ep_num FROM episodes WHERE anime_code = ? ORDER BY ep_num ASC", (a_code,)).fetchall()
        last_ep = get_last_episode(user_id, a_code)
        markup = types.InlineKeyboardMarkup(row_width=5)
        btns = []
        for e in eps:
            text = str(e[0])
            if last_ep == e[0]:
                text += " ✓"
            btns.append(types.InlineKeyboardButton(text, callback_data=f"ep_{a_code}_{e[0]}"))
        if btns:
            markup.add(*btns)
        markup.add(types.InlineKeyboardButton("• Yuklab Olish •", url=f"https://t.me/{BOT_USERNAME}?start={a_code}"))
        bot.send_photo(message.chat.id, photo, caption=f"🎬 <b>{title}</b>\n\n📌 Kodi: {a_code}\n👁 Ko'rildi: {views if views else 0}", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Kechirasiz, bunday kodli anime topilmadi.")

@bot.message_handler(func=lambda m: m.text.isdigit())
def search_by_digit(message):
    show_anime_by_code(message, message.text)

@bot.callback_query_handler(func=lambda call: call.data.startswith('ep_'))
def play_video(call):
    _, code, num = call.data.split('_')
    user_id = call.from_user.id
    conn, cursor = get_db()
    video = cursor.execute("SELECT video_id FROM episodes WHERE anime_code = ? AND ep_num = ?", (code, num)).fetchone()
    if video:
        bot.send_video(call.message.chat.id, video[0], caption=f"🎬 <b>{code}</b> | {num}-qism")
        # Foydalanuvchining so‘nggi ko‘rgan qismini yangilash
        update_last_episode(user_id, code, int(num))
    else:
        bot.answer_callback_query(call.id, "Video topilmadi!")

# Top animelar
@bot.message_handler(func=lambda m: m.text == "🔥 Top Animelar")
def top_animes(message):
    if not check_subscription(message):
        return
    send_top_page(message.chat.id, 0)

def send_top_page(chat_id, offset, message_id=None):
    conn, cursor = get_db()
    total_animes = cursor.execute("SELECT COUNT(*) FROM animes").fetchone()[0]
    animes = cursor.execute("""
        SELECT code, title, views
        FROM animes
        ORDER BY views DESC
        LIMIT 10 OFFSET ?""", (offset,)).fetchall()
    if not animes:
        bot.send_message(chat_id, "Bazada hali animelar yo'q.")
        return
    text = f"🔥 <b>Eng ko'p ko'rilgan animelar:</b>\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, a in enumerate(animes, start=offset + 1):
        text += f"{i}. {a[1]} — (👁 {a[2]})\n"
        markup.add(types.InlineKeyboardButton(f"🎬 {a[1]} (Kod: {a[0]})", callback_data=f"show_{a[0]}"))
    nav_btns = []
    if offset > 0:
        nav_btns.append(types.InlineKeyboardButton("⬅️ Orqaga", callback_data=f"top_{offset-10}"))
    if offset + 10 < total_animes:
        nav_btns.append(types.InlineKeyboardButton("Keyingisi ➡️", callback_data=f"top_{offset+10}"))
    if nav_btns:
        markup.row(*nav_btns)
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('top_'))
def top_callback(call):
    offset = int(call.data.split('_')[1])
    send_top_page(call.message.chat.id, offset, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('show_'))
def show_callback(call):
    code = call.data.split('_')[1]
    show_anime_by_code(call.message, code)

# ==================== PREMIUM SOZLAMALARI ====================
@bot.message_handler(func=lambda m: m.text == "💎 Premium Sozlamalari")
def premium_settings(message):
    perms = get_admin_perms(message.from_user.id)
    if not perms or not perms['premium']:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⭐ Animeni Premium qilish", callback_data="make_anime_prem"),
        types.InlineKeyboardButton("👤 Foydalanuvchiga Premium berish", callback_data="make_user_prem")
    )
    bot.send_message(message.chat.id, "💎 <b>Premium boshqaruv bo'limi:</b>", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "make_anime_prem")
def prem_anime_list(call):
    perms = get_admin_perms(call.from_user.id)
    if not perms or not perms['premium']:
        return bot.answer_callback_query(call.id, "Sizda bu ruxsat yo'q!", show_alert=True)
    conn, cursor = get_db()
    animes = cursor.execute("SELECT code, title FROM animes WHERE is_premium = 0").fetchall()
    if not animes:
        return bot.answer_callback_query(call.id, "Hamma animelar premium yoki baza bo'sh!", show_alert=True)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for a in animes:
        markup.add(types.InlineKeyboardButton(f"💎 {a[1]}", callback_data=f"setprem_an_{a[0]}"))
    bot.edit_message_text("💎 <b>Premium qilmoqchi bo'lgan animengizni tanlang:</b>",
                          call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('setprem_an_'))
def prem_anime_exec(call):
    perms = get_admin_perms(call.from_user.id)
    if not perms or not perms['premium']:
        return bot.answer_callback_query(call.id, "Sizda bu ruxsat yo'q!", show_alert=True)
    code = call.data.split('_')[2]
    conn, cursor = get_db()
    cursor.execute("UPDATE animes SET is_premium = 1 WHERE code = ?", (code,))
    conn.commit()
    bot.answer_callback_query(call.id, "Anime premium bo'ldi!")
    bot.edit_message_text(f"✅ Kod: {code} bo'lgan anime <b>Premium</b> qilindi!", call.message.chat.id, call.message.message_id, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "make_user_prem")
def prem_user_ask(call):
    perms = get_admin_perms(call.from_user.id)
    if not perms or not perms['premium']:
        return bot.answer_callback_query(call.id, "Sizda bu ruxsat yo'q!", show_alert=True)
    msg = bot.send_message(call.message.chat.id, "👤 <b>Premium bermoqchi bo'lgan foydalanuvchi ID raqamini yuboring:</b>\n(ID-ni statistikadan olishingiz mumkin)", parse_mode='HTML')
    bot.register_next_step_handler(msg, prem_user_exec)

def prem_user_exec(message):
    user_id = message.text
    if not user_id.isdigit():
        return bot.send_message(message.chat.id, "❌ Faqat ID raqamini yuboring!", reply_markup=admin_kb(message.from_user.id))
    conn, cursor = get_db()
    cursor.execute("UPDATE users SET status = 'premium' WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(message.chat.id, f"✅ Foydalanuvchi {user_id} muvaffaqiyatli <b>Premium</b> qilindi!", reply_markup=admin_kb(message.from_user.id), parse_mode='HTML')
    try:
        bot.send_message(int(user_id), "🎉 <b>Tabriklaymiz! Admin sizga Premium statusini berdi!</b>\nEndi barcha animelar siz uchun ochiq.", parse_mode='HTML')
    except: pass

# ==================== FOYDALANUVCHIGA XABAR YUBORISH ====================
@bot.message_handler(func=lambda m: m.text == "📩 Foydalanuvchiga yozish")
def list_users_for_msg(message):
    perms = get_admin_perms(message.from_user.id)
    if not perms or not perms['write_user']:
        return
    send_user_list_page(message.chat.id, 0, user_id=message.from_user.id)

def send_user_list_page(chat_id, offset, user_id, message_id=None):
    conn, cursor = get_db()
    total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    users = cursor.execute("SELECT user_id, username FROM users LIMIT 10 OFFSET ?", (offset,)).fetchall()
    if not users:
        return bot.send_message(chat_id, "❌ Bazada foydalanuvchilar topilmadi.")
    markup = types.InlineKeyboardMarkup(row_width=1)
    for u in users:
        # Username qanaqa bo'lishidan qat'i nazar, faqat ID ni tugmada ko'rsatamiz
        markup.add(types.InlineKeyboardButton(f"👤 ID: {u[0]}", callback_data=f"msguser_{u[0]}"))
    nav_btns = []
    if offset > 0:
        nav_btns.append(types.InlineKeyboardButton("⬅️ Orqaga", callback_data=f"usrs_{offset-10}"))
    if offset + 10 < total_users:
        nav_btns.append(types.InlineKeyboardButton("Keyingisi ➡️", callback_data=f"usrs_{offset+10}"))
    if nav_btns:
        markup.row(*nav_btns)
    text = "👤 <b>Xabar yubormoqchi bo'lgan foydalanuvchini tanlang:</b>"
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('usrs_'))
def user_list_callback(call):
    offset = int(call.data.split('_')[1])
    send_user_list_page(call.message.chat.id, offset, call.from_user.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('msguser_'))
def ask_admin_message(call):
    perms = get_admin_perms(call.from_user.id)
    if not perms or not perms['write_user']:
        return bot.answer_callback_query(call.id, "Sizda bu ruxsat yo'q!", show_alert=True)
    target_id = call.data.split('_')[1]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id,
                           f"📝 <b>ID: {target_id} bo'lgan foydalanuvchiga xabaringizni yozing:</b>\n\n(Bekor qilish uchun tugmani bosing)",
                           reply_markup=cancel_kb(), parse_mode='HTML')
    bot.register_next_step_handler(msg, send_final_msg_to_user, target_id)

def send_final_msg_to_user(message, target_id):
    if message.text == "🚫 Bekor qilish":
        return bot.send_message(message.chat.id, "❌ Bekor qilindi.", reply_markup=admin_kb(message.from_user.id))
    try:
        full_msg = f"📩 <b>Admindan xabar keldi:</b>\n\n{message.text}"
        bot.send_message(int(target_id), full_msg, parse_mode='HTML')
        bot.send_message(message.chat.id, f"✅ Xabar (ID: {target_id}) ga muvaffaqiyatli yuborildi!", reply_markup=admin_kb(message.from_user.id))
        print(f"📧 ADMIN_MSG: {target_id} ga xabar yubordi.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik! Foydalanuvchi botni bloklagan bo'lishi mumkin.\n\n{e}", reply_markup=admin_kb(message.from_user.id))

# ==================== ADMINGA MUROJAAT VA LIMIT ====================
@bot.message_handler(func=lambda m: m.text == "✍️ Adminga murojaat")
def support_start(message):
    u_id = message.from_user.id
    conn, cursor = get_db()
    now = datetime.datetime.now()
    user_limit = cursor.execute("SELECT last_reset, msg_count FROM support_limits WHERE user_id = ?", (u_id,)).fetchone()
    msg_count = 0
    last_reset = None
    if user_limit:
        last_reset_str, msg_count = user_limit
        if last_reset_str:
            last_reset = datetime.datetime.strptime(last_reset_str, '%Y-%m-%d %H:%M:%S')
            if (now - last_reset).total_seconds() > 3600:
                cursor.execute("UPDATE support_limits SET last_reset = ?, msg_count = 0 WHERE user_id = ?",
                               (now.strftime('%Y-%m-%d %H:%M:%S'), u_id))
                conn.commit()
                msg_count = 0
                last_reset = now
    if msg_count >= 5:
        diff = 3600 - (now - last_reset).total_seconds() if last_reset else 3600
        minutes = int(diff // 60)
        return bot.send_message(message.chat.id, f"⚠️ <b>Limitga yetdingiz!</b>\n\nSiz 1 soatda faqat 5 ta xabar yubora olasiz. Yana {minutes} daqiqadan so'ng yozishingiz mumkin.")
    msg = bot.send_message(message.chat.id, "📝 <b>Adminga yubormoqchi bo'lgan xabaringizni yozing:</b>\n(Xabaringiz to'g'ridan-to'g'ri adminga boradi)", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, send_to_admin)

def send_to_admin(message):
    if message.text == "🚫 Bekor qilish":
        return bot.send_message(message.chat.id, "Bekor qilindi.", reply_markup=main_kb(message.from_user.id))
    u_id = message.from_user.id
    conn, cursor = get_db()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        INSERT INTO support_limits (user_id, last_reset, msg_count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id) DO UPDATE SET
        msg_count = COALESCE(msg_count, 0) + 1,
        last_reset = excluded.last_reset
    """, (u_id, now))
    conn.commit()
    admin_text = f"📩 <b>Yangi murojaat!</b>\n\n<b>Kimdan:</b> <a href='tg://user?id={u_id}'>{message.from_user.first_name}</a>\n<b>ID:</b> <code>{u_id}</code>\n\n<b>Xabar:</b> {message.text}"
    # Barcha adminlarga yuborish (super admin va boshqalar)
    bot.send_message(ADMIN_ID, admin_text, parse_mode='HTML')
    # Agar boshqa adminlar bo'lsa, ularga ham yuborish
    conn, cursor = get_db()
    admins = cursor.execute("SELECT user_id FROM admins WHERE user_id != ?", (ADMIN_ID,)).fetchall()
    for a in admins:
        try:
            bot.send_message(a[0], admin_text, parse_mode='HTML')
        except:
            pass
    bot.send_message(message.chat.id, "✅ <b>Xabaringiz adminga yuborildi!</b>\nTez orada javob qaytaramiz.", reply_markup=main_kb(u_id))
    print(f"📩 MUROJAAT: {u_id} dan xabar keldi.")

# ==================== TEZKOR QISM QO'SHISH LOGIKASI ====================
bulk_upload_data = {}

@bot.message_handler(func=lambda m: m.text == "⚡️ Tezkor yuklash")
def bulk_start(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "🎬 <b>Anime kodini yuboring:</b>", parse_mode="HTML", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, bulk_get_code)

def bulk_get_code(message):
    if message.text == "🚫 Bekor qilish":
        return bot.send_message(message.chat.id, "Bekor qilindi.", reply_markup=admin_kb(message.from_user.id))
    
    anime_code = message.text
    
    # KODNI TEKSHIRISH (Dublikat yoki borligini bilish uchun)
    conn, cursor = get_db()
    cursor.execute("SELECT title FROM animes WHERE code = ?", (anime_code,))
    anime = cursor.fetchone()
    conn.close()

    if not anime:
        return bot.send_message(message.chat.id, f"❌ <b>{anime_code}</b> kodli anime topilmadi! Avval animeni qo'shing.")

    # REJIM TANLASH TUGMALARI
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("1️⃣ Bittalab", callback_data=f"bmode_single_{anime_code}"),
        types.InlineKeyboardButton("🔢 Hammasini birdan", callback_data=f"bmode_multi_{anime_code}")
    )
    bot.send_message(message.chat.id, f"🎬 Anime: <b>{anime[0]}</b>\nYuklash turini tanlang:", reply_markup=markup, parse_mode="HTML")

# Tanlangan rejimni tutib olib, nechanchi qismligini so'rash
@bot.callback_query_handler(func=lambda call: call.data.startswith('bmode_'))
def bulk_ask_ep_num(call):
    _, mode, code = call.data.split('_')
    msg = bot.send_message(call.message.chat.id, "🔢 Nechanchi qismdan boshlaymiz?")
    bot.register_next_step_handler(msg, bulk_get_start_ep_new, code, mode)

def bulk_get_start_ep_new(message, anime_code, mode):
    try:
        start_ep = int(message.text)
        # Rejimni ham xotiraga saqlaymiz
        bulk_upload_data[message.from_user.id] = {'code': anime_code, 'next_ep': start_ep, 'mode': mode}
        msg = bot.send_message(message.chat.id, f"✅ Tayyor! Endi videolarni yuboring.\nRejim: {'Hammasini birdan' if mode == 'multi' else 'Bittalab'}\nTo'xtatish: <b>/stop</b>", parse_mode="HTML")
        bot.register_next_step_handler(msg, bulk_save_loop)
    except:
        bot.send_message(message.chat.id, "Faqat raqam yozing!")

def bulk_get_start_ep(message, anime_code):
    try:
        start_ep = int(message.text)
        bulk_upload_data[message.from_user.id] = {'code': anime_code, 'next_ep': start_ep}
        msg = bot.send_message(message.chat.id, f"✅ Tayyor! Endi qismlarni ketma-ket yuboring.\nTo'xtatish uchun: <b>/stop</b>", parse_mode="HTML")
        bot.register_next_step_handler(msg, bulk_save_loop)
    except:
        bot.send_message(message.chat.id, "Faqat raqam yozing!")

def bulk_save_loop(message):
    user_id = message.from_user.id
    if message.text == "/stop":
        bulk_upload_data.pop(user_id, None)
        return bot.send_message(message.chat.id, "🛑 Tugatildi.", reply_markup=admin_kb(user_id))

    if not message.video:
        msg = bot.send_message(message.chat.id, "⚠️ Video yuboring yoki /stop bosing.")
        bot.register_next_step_handler(msg, bulk_save_loop)
        return

    data = bulk_upload_data.get(user_id)
    anime_code, ep_num, mode = data['code'], data['next_ep'], data['mode']

    conn, cursor = get_db()
    cursor.execute("INSERT INTO episodes (anime_code, ep_num, video_id) VALUES (?, ?, ?)", (anime_code, ep_num, message.video.file_id))
    conn.commit()
    conn.close()

    bulk_upload_data[user_id]['next_ep'] += 1
    
    if mode == 'single':
        # Har biriga reply qaytaradi
        msg = bot.reply_to(message, f"✅ {ep_num}-qism saqlandi! Keyingisini yuboring...")
    else:
        # Faqat kichik xabar (reaksiya o'rnida)
        msg = bot.send_message(message.chat.id, f"📥 {ep_num}-qism kiritildi...")
    
    bot.register_next_step_handler(msg, bulk_save_loop)
        return

    data = bulk_upload_data.get(user_id)
    anime_code, ep_num = data['code'], data['next_ep']

    conn, cursor = get_db()
    cursor.execute("INSERT INTO episodes (anime_code, ep_num, video_id) VALUES (?, ?, ?)", (anime_code, ep_num, message.video.file_id))
    conn.commit()

    bulk_upload_data[user_id]['next_ep'] += 1
    msg = bot.reply_to(message, f"✅ {ep_num}-qism saqlandi! Keyingisini yuboring...")
    bot.register_next_step_handler(msg, bulk_save_loop)
    
# ==================== FLASK SERVER ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlamoqda!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# ==================== BOTNI ISHGA TUSHIRISH ====================
if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("🚀 Bot muvaffaqiyatli ishga tushdi...")
    try:
        bot.infinity_polling(allowed_updates=["message", "callback_query", "chat_join_request"])
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
