import telebot
import sqlite3
from telebot import types

# 1. SOZLAMALAR
BOT_TOKEN = "8463516034:AAF0S0e8_6M8XhlmqFTpmrbOcIddOxh19i0"
ADMIN_ID = 7878240647
BOT_USERNAME = "Anishadowmythicbot"

# Zayavka kanalingiz ID-si va havolasi
KANAL_ID = -1002361622352          # Agar bu ID to'g'ri bo'lsa, o'zgartirmang
ZAYAVKA_LINK = "https://t.me/+O08QOzg7QSo1YzEy"   # Yangi link

# Botni aniqlash
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# 2. BAZA (Database)
def get_db():
    conn = sqlite3.connect('anishadow_final.db', check_same_thread=False)
    return conn, conn.cursor()

def init_db():
    conn, cursor = get_db()

    # 1. Asosiy jadvallar
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS animes (code TEXT PRIMARY KEY, title TEXT, photo_id TEXT, views INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS episodes (anime_code TEXT, ep_num INTEGER, video_id TEXT)')

    # 2. Support (Adminga murojaat) limiti uchun jadval
    cursor.execute('''CREATE TABLE IF NOT EXISTS support_limits
                     (user_id INTEGER PRIMARY KEY, last_reset TEXT, msg_count INTEGER DEFAULT 0)''')

    # 3. Zayavkalar (Requests) uchun jadval
    cursor.execute('CREATE TABLE IF NOT EXISTS requests (user_id INTEGER PRIMARY KEY)')

    # 4. Mavjud bazaga yangi ustunlarni qo'shish
    try: cursor.execute('ALTER TABLE users ADD COLUMN username TEXT')
    except: pass
    try: cursor.execute('ALTER TABLE users ADD COLUMN status TEXT DEFAULT "free"')
    except: pass
    try: cursor.execute('ALTER TABLE animes ADD COLUMN views INTEGER DEFAULT 0')
    except: pass
    try: cursor.execute('ALTER TABLE animes ADD COLUMN is_premium INTEGER DEFAULT 0')
    except: pass

    conn.commit()

# Bazani ishga tushirish
init_db()

# --- 3. TEKSHIRUV FUNKSIYASI ---
def is_subscribed(user_id):
    # Admin botdan doim to'siqsiz foydalana oladi
    if str(user_id) == str(ADMIN_ID):
        return True

    # 1. Kanalda a'zomi?
    try:
        status = bot.get_chat_member(KANAL_ID, user_id).status
        if status in ['member', 'administrator', 'creator']:
            return True
    except:
        pass

    # 2. Bazada zayavkasi bormi?
    conn, cursor = get_db()
    res = cursor.execute("SELECT user_id FROM requests WHERE user_id = ?", (user_id,)).fetchone()
    if res:
        return True

    return False

# --- 4. ZAYAVKALARNI BAZAGA YOZISH (Sizda shu qism yo'q edi) ---
@bot.chat_join_request_handler()
def handle_join_request(chat_join_request):
    u_id = chat_join_request.from_user.id
    conn, cursor = get_db()
    cursor.execute("INSERT OR IGNORE INTO requests (user_id) VALUES (?)", (u_id,))
    conn.commit()
    print(f"✅ ZAYAVKA TUSHDI: {u_id} bazaga saqlandi.")

# 3. KLAVIATURALAR
def main_kb(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔍 Anime izlash", "🔥 Top Animelar")
    kb.add("📚 Qo'llanma", "✍️ Adminga murojaat") # Yangi tugma
    kb.add("💵 Reklama va Homiy")
    if user_id == ADMIN_ID:
        kb.add("⚙️ Admin Panel")
    return kb

def admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("➕ Anime yuklash", "🎬 Qism qo'shish")
    kb.add("📊 Statistika", "📢 Reklama yuborish")
    kb.add("🗑 Anime o'chirish", "🎬 Qismni o'chirish")
    kb.add("💎 Premium Sozlamalari", "📩 Foydalanuvchiga yozish") # Yangi tugma
    kb.add("🏠 Bosh menyu")
    return kb
def cancel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🚫 Bekor qilish")
    return kb

# 4. FOYDALANUVCHI MENYUSI (QO'LLANMA VA REKLAMA)
@bot.message_handler(func=lambda m: m.text == "💵 Reklama va Homiy")
def ad_sponsor(message):
    text = f"🤝 <b>Reklama va Homiylik masalalari bo'yicha:</b>\n\nIltimos, to'g'ridan-to'g'ri adminga yozing:"
    markup = types.InlineKeyboardMarkup()
    # ID orqali to'g'ridan-to'g'ri lichkaga o'tish tugmasi
    markup.add(types.InlineKeyboardButton("👤 Adminga yozish", url=f"tg://user?id={ADMIN_ID}"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📚 Qo'llanma")
def guide(message):
    text = """📚 <b>Botdan foydalanish qo'llanmasi:</b>

1️⃣ <b>Anime qidirish:</b> Kanalimizdan ko'rmoqchi bo'lgan animengiz kodini toping (Masalan: 101).
2️⃣ <b>Kodni yozish:</b> Botga o'sha raqamni yuboring.
3️⃣ <b>Qismlarni ko'rish:</b> Anime kelib chiqqandan so'ng, rasm ostidagi raqamlarni (1, 2, 3...) bossangiz, o'sha qism videosi keladi.

<i>Agar biror muammo bo'lsa, "Reklama va Homiy" bo'limi orqali adminga yozishingiz mumkin.</i>"""
    bot.send_message(message.chat.id, text)

# 5. START VA START MATNI
# 5. START VA START MATNI
@bot.message_handler(commands=['start'])
def welcome(message):
    conn, cursor = get_db()

    # Foydalanuvchi ma'lumotlarini olish
    u_id = message.from_user.id
    u_name = message.from_user.username if message.from_user.username else "yo'q"

    # Bazaga tekshirib qo'shish yoki yangilash
    cursor.execute("INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)", (u_id, u_name))
    conn.commit()

    # Deep-link (yo'naltirilgan havola) orqali kirsa
    args = message.text.split()
    if len(args) > 1:
        anime_code = args[1]
        show_anime_by_code(message, anime_code)
        return

    # Oddiy start bosilganda chiqadigan xabar
    text = f"""👋 <b>Assalomu alaykum, {message.from_user.first_name}!</b>

Men siz qidirayotgan barcha Animelarni topishga yordam beraman. Buning uchun Anime kodini aniq yozishingiz kerak!

☝️ <b>Masalan:</b> 1 yoki 101
📢 <b>Kanalimiz:</b> @AniShadowMythic

✅ <i>Tushungan bo'lsangiz, Anime kodini yuboring!</i>"""

    bot.send_message(message.chat.id, text, reply_markup=main_kb(u_id))
# 6. ADMIN PANEL
@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel" and m.from_user.id == ADMIN_ID)
def open_admin(message):
    bot.send_message(message.chat.id, "👨‍💻 Admin panelga xush kelibsiz:", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "🏠 Bosh menyu")
def back_home(message):
    bot.send_message(message.chat.id, "Bosh menyuga qaytdik.", reply_markup=main_kb(message.from_user.id))

# BU YERDA BO'SH QATOR QOLDIRING (Ixtiyoriy, lekin chiroyli chiqadi)

@bot.message_handler(func=lambda m: m.text == "📊 Statistika" and m.from_user.id == ADMIN_ID)
def show_stats(message):
    conn, cursor = get_db()

    # 1. Umumiy sonlarni olish
    total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_animes = cursor.execute("SELECT COUNT(*) FROM animes").fetchone()[0]

    # 2. Oxirgi 10 ta foydalanuvchini olish
    last_users = cursor.execute("SELECT user_id, username FROM users ORDER BY rowid DESC LIMIT 10").fetchall()
    u_text = ""
    for u in last_users:
        # ID-ni bosiladigan linkka aylantiramiz (tg://user?id=...)
        user_link = f'<a href="tg://user?id={u[0]}">{u[0]}</a>'

        # Username None bo'lsa yoki bo'sh bo'lsa "yo'q" deb ko'rsatamiz
        username = f"@{u[1]}" if u[1] and u[1] != "yo'q" else "username yo'q"

        u_text += f"👤 {user_link} | {username}\n"

    # 3. Top 5 ta ko'p ko'rilgan anime
    top_animes = cursor.execute("SELECT title, views FROM animes ORDER BY views DESC LIMIT 5").fetchall()
    a_text = ""
    for a in top_animes:
        a_text += f"🎬 {a[0]} — {a[1]} marta\n"

    # Natijani yuborish
    text = f"📊 <b>Bot Statistikasi</b>\n\n" \
           f"👥 Jami foydalanuvchilar: {total_users}\n" \
           f"🎬 Jami animelar: {total_animes}\n\n" \
           f"🔝 <b>Eng ko'p ko'rilganlar:</b>\n{a_text if a_text else 'Hali ko`rilmagan'}\n\n" \
           f"🆕 <b>Oxirgi kirganlar (ID ustiga bosing):</b>\n{u_text}"

    bot.send_message(message.chat.id, text, parse_mode='HTML')

# --- SHU YERDAN REKLAMA KODINI QO'SHASIZ ---
@bot.message_handler(func=lambda m: m.text == "📢 Reklama yuborish" and m.from_user.id == ADMIN_ID)
def start_broadcast(message):
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

    bot.send_message(message.chat.id, f"✅ Reklama {count} kishiga yuborildi!", reply_markup=admin_kb())

# 7. ANIME YUKLASH (Bekor qilish tugmasi bilan)
@bot.message_handler(func=lambda m: m.text == "➕ Anime yuklash" and m.from_user.id == ADMIN_ID)
def add_step_1(message):
    msg = bot.send_message(message.chat.id, "<b>1. Anime uchun POSTER (rasm) yuboring:</b>", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, add_step_2)

def add_step_2(message):
    if message.text == "🚫 Bekor qilish":
        return bot.send_message(message.chat.id, "❌ Yuklash bekor qilindi.", reply_markup=admin_kb())

    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ Faqat rasm yuboring! Yoki jarayonni bekor qiling:", reply_markup=cancel_kb())
        bot.register_next_step_handler(msg, add_step_2)
        return

    photo_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "<b>2. Anime uchun KOD kiriting (Masalan: 101):</b>", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, add_step_3, photo_id)

def add_step_3(message, photo_id):
    if message.text == "🚫 Bekor qilish":
        return bot.send_message(message.chat.id, "❌ Yuklash bekor qilindi.", reply_markup=admin_kb())

    code = message.text
    msg = bot.send_message(message.chat.id, "<b>3. Anime NOMINI kiriting:</b>", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, add_step_final, photo_id, code)

def add_step_final(message, photo_id, code):
    if message.text == "🚫 Bekor qilish":
        return bot.send_message(message.chat.id, "❌ Yuklash bekor qilindi.", reply_markup=admin_kb())

    title = message.text
    conn, cursor = get_db()
    cursor.execute("INSERT OR REPLACE INTO animes (code, title, photo_id) VALUES (?, ?, ?)", (code, title, photo_id))
    conn.commit()

    # --- TERMINAL MONITORING ---
    admin_name = message.from_user.first_name
    admin_id = message.from_user.id
    print(f"➕ YANGI ANIME: {title} (Kod: {code}) | Yukladi: {admin_name} (ID: {admin_id})")
    # ---------------------------

    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.send_message(message.chat.id, f"✅ <b>Anime saqlandi!</b>\n\n🎬 Nomi: {title}\n📌 Kodi: {code}\n🔗 Havola: <code>{link}</code>", reply_markup=admin_kb())
# # 8. QISM QO'SHISH (Bekor qilish tugmasi bilan)
@bot.message_handler(func=lambda m: m.text == "🎬 Qism qo'shish" and m.from_user.id == ADMIN_ID)
def ep_step_1(message):
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
        return bot.send_message(message.chat.id, "❌ Qism qo'shish bekor qilindi.", reply_markup=admin_kb())

    num = message.text
    if not num.isdigit():
        msg = bot.send_message(message.chat.id, "❌ Iltimos, faqat RAQAM yozing! (Yoki bekor qiling):", reply_markup=cancel_kb())
        bot.register_next_step_handler(msg, ep_step_3, code)
        return

    msg = bot.send_message(message.chat.id, f"<b>{num}-qism VIDEOSINI yuboring:</b>", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, ep_step_final, code, num)

def ep_step_final(message, code, num):
    if message.text == "🚫 Bekor qilish":
        return bot.send_message(message.chat.id, "❌ Qism qo'shish bekor qilindi.", reply_markup=admin_kb())

    if message.content_type != 'video':
        msg = bot.send_message(message.chat.id, "❌ Faqat video yuboring! (Yoki bekor qiling):", reply_markup=cancel_kb())
        bot.register_next_step_handler(msg, ep_step_final, code, num)
        return

    conn, cursor = get_db()
    cursor.execute("INSERT INTO episodes VALUES (?, ?, ?)", (code, int(num), message.video.file_id))
    conn.commit()

    # --- TERMINAL MONITORING ---
    admin_name = message.from_user.first_name
    admin_id = message.from_user.id
    print(f"🎬 YANGI QISM: {code}-kodli animega {num}-qism qo'shildi | Yukladi: {admin_name} (ID: {admin_id})")
    # ---------------------------

    bot.send_message(message.chat.id, f"✅ <b>{code}</b>-anime uchun <b>{num}</b>-qism muvaffaqiyatli saqlandi!", reply_markup=admin_kb())
# 9. QIDIRUV VA VIDEO KO'RISH
def show_anime_by_code(message, code):
    conn, cursor = get_db()

    # Ko'rishlar sonini oshirish
    cursor.execute("UPDATE animes SET views = views + 1 WHERE code = ?", (code,))
    conn.commit()

    # Bazadan hamma ma'lumotni olamiz
    anime = cursor.execute("SELECT code, title, photo_id, views FROM animes WHERE code = ?", (code,)).fetchone()

    if anime:
        # ENDI 4 TA MA'LUMOTNI QABUL QILAMIZ:
        a_code, title, photo, views = anime

        eps = cursor.execute("SELECT ep_num FROM episodes WHERE anime_code = ? ORDER BY ep_num ASC", (a_code,)).fetchall()
        markup = types.InlineKeyboardMarkup(row_width=5)
        btns = [types.InlineKeyboardButton(str(e[0]), callback_data=f"ep_{a_code}_{e[0]}") for e in eps]
        markup.add(*btns)

        # Yuklab olish tugmasini ham qo'shib qo'yamiz
        markup.add(types.InlineKeyboardButton("• Yuklab Olish •", url=f"https://t.me/{BOT_USERNAME}?start={a_code}"))

        # Captionda ko'rishlar sonini ham ko'rsatamiz
        bot.send_photo(message.chat.id, photo, caption=f"🎬 <b>{title}</b>\n\n📌 Kodi: {a_code}\n👁 Ko'rildi: {views if views else 0}", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Kechirasiz, bunday kodli anime topilmadi.")

@bot.message_handler(func=lambda m: m.text == "🔍 Anime izlash")
def search_handler(message):
    bot.send_message(message.chat.id, "Anime kodini yuboring (Masalan: 101):")

@bot.message_handler(func=lambda m: m.text.isdigit())
def search_by_digit(message):
    show_anime_by_code(message, message.text)

@bot.callback_query_handler(func=lambda call: call.data.startswith('ep_'))
def play_video(call):
    _, code, num = call.data.split('_')
    conn, cursor = get_db()
    video = cursor.execute("SELECT video_id FROM episodes WHERE anime_code = ? AND ep_num = ?", (code, num)).fetchone()
    if video:
        bot.send_video(call.message.chat.id, video[0], caption=f"🎬 <b>{code}</b> | {num}-qism")
    else:
        bot.answer_callback_query(call.id, "Video topilmadi!")
# ... tepadagi boshqa kodlaringiz ...
# --- TOP ANIMELAR VA SAHIFALASH ---

@bot.message_handler(func=lambda m: m.text == "🔥 Top Animelar")
def top_animes(message):
    send_top_page(message.chat.id, 0) # Birinchi sahifani yuboramiz (offset = 0)

def send_top_page(chat_id, offset, message_id=None):
    conn, cursor = get_db()

    # Jami animelar sonini aniqlaymiz
    total_animes = cursor.execute("SELECT COUNT(*) FROM animes").fetchone()[0]

    # 10 ta animeni views bo'yicha kamayish tartibida olamiz
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
        # Ro'yxat ko'rinishi
        text += f"{i}. {a[1]} — (👁 {a[2]})\n"
        # Har bir animega to'g'ridan-to'g'ri o'tish tugmasi
        markup.add(types.InlineKeyboardButton(f"🎬 {a[1]} (Kod: {a[0]})", callback_data=f"show_{a[0]}"))

    # Navigatsiya tugmalari (Orqaga va Keyingisi)
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

# Tugmalar bosilganda sahifani yangilash
@bot.callback_query_handler(func=lambda call: call.data.startswith('top_'))
def top_callback(call):
    offset = int(call.data.split('_')[1])
    send_top_page(call.message.chat.id, offset, call.message.message_id)

# Ro'yxatdagi anime tugmasini bossa o'sha animeni ko'rsatish
@bot.callback_query_handler(func=lambda call: call.data.startswith('show_'))
def show_callback(call):
    code = call.data.split('_')[1]
    show_anime_by_code(call.message, code)

# --- 10. ANIME O'CHIRISH (POLINGDAN TEPADA) ---
@bot.message_handler(func=lambda m: m.text == "🗑 Anime o'chirish" and m.from_user.id == ADMIN_ID)
def delete_anime_list(message):
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
    anime_code = call.data.split('_')[1]
    conn, cursor = get_db()
    cursor.execute("DELETE FROM animes WHERE code = ?", (anime_code,))
    cursor.execute("DELETE FROM episodes WHERE anime_code = ?", (anime_code,))
    conn.commit()

    bot.answer_callback_query(call.id, "O'chirildi!")
    bot.edit_message_text(f"✅ Kod: {anime_code} bazadan o'chirildi.", call.message.chat.id, call.message.message_id)
# --- QISMNI O'CHIRISH BOSHLANISHI ---

# 1. Animeni tanlash (Qismni o'chirish uchun)
@bot.message_handler(func=lambda m: m.text == "🎬 Qismni o'chirish" and m.from_user.id == ADMIN_ID)
def delete_ep_start(message):
    conn, cursor = get_db()
    animes = cursor.execute("SELECT code, title FROM animes").fetchall()

    if not animes:
        return bot.send_message(message.chat.id, "❌ Bazada birorta ham anime yo'q.")

    markup = types.InlineKeyboardMarkup(row_width=1)
    for a in animes:
        # Callback: epdel_list_{kod}
        markup.add(types.InlineKeyboardButton(f"🎬 {a[1]}", callback_data=f"epdel_list_{a[0]}"))

    bot.send_message(message.chat.id, "<b>Qaysi animening qismini o'chirmoqchisiz?</b>", reply_markup=markup, parse_mode='HTML')

# 2. Tanlangan animening qismlarini ko'rsatish
@bot.callback_query_handler(func=lambda call: call.data.startswith('epdel_list_'))
def delete_ep_select(call):
    anime_code = call.data.split('_')[2]
    conn, cursor = get_db()

    # Shu animega tegishli hamma qismlarni olamiz
    eps = cursor.execute("SELECT ep_num FROM episodes WHERE anime_code = ? ORDER BY ep_num ASC", (anime_code,)).fetchall()

    if not eps:
        return bot.answer_callback_query(call.id, "Bu animeda hali qismlar yo'q!", show_alert=True)

    markup = types.InlineKeyboardMarkup(row_width=5)
    btns = []
    for e in eps:
        # Callback: epdel_exec_{kod}_{qism_raqami}
        btns.append(types.InlineKeyboardButton(f"{e[0]}", callback_data=f"epdel_exec_{anime_code}_{e[0]}"))

    markup.add(*btns)
    markup.add(types.InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_del_anime"))

    bot.edit_message_text(f"🔢 <b>Kod: {anime_code}</b>\n\nO'chirmoqchi bo'lgan qismingizni tanlang:",
                          call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

# 3. Qismni o'chirishni bajarish
@bot.callback_query_handler(func=lambda call: call.data.startswith('epdel_exec_'))
def delete_ep_final(call):
    data = call.data.split('_')
    anime_code = data[2]
    ep_num = data[3]

    conn, cursor = get_db()
    # Faqat bitta qismni o'chirish
    cursor.execute("DELETE FROM episodes WHERE anime_code = ? AND ep_num = ?", (anime_code, ep_num))
    conn.commit()

    bot.answer_callback_query(call.id, f"{ep_num}-qism o'chirildi!", show_alert=True)

    # Ro'yxatni yangilash (qolgan qismlarni qayta ko'rsatish)
    delete_ep_select(call)
    # 11. PREMIUM BOSHQARUV PANELI
@bot.message_handler(func=lambda m: m.text == "💎 Premium Sozlamalari" and m.from_user.id == ADMIN_ID)
def premium_settings(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⭐ Animeni Premium qilish", callback_data="make_anime_prem"),
        types.InlineKeyboardButton("👤 Foydalanuvchiga Premium berish", callback_data="make_user_prem")
    )
    bot.send_message(message.chat.id, "💎 <b>Premium boshqaruv bo'limi:</b>", reply_markup=markup, parse_mode='HTML')

# --- Animeni Premium qilish (Ro'yxatdan tanlash) ---
@bot.callback_query_handler(func=lambda call: call.data == "make_anime_prem")
def prem_anime_list(call):
    conn, cursor = get_db()
    # Faqat hali premium bo'lmagan animelarni chiqaramiz
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
    code = call.data.split('_')[2]
    conn, cursor = get_db()
    cursor.execute("UPDATE animes SET is_premium = 1 WHERE code = ?", (code,))
    conn.commit()
    bot.answer_callback_query(call.id, "Anime premium bo'ldi!")
    bot.edit_message_text(f"✅ Kod: {code} bo'lgan anime <b>Premium</b> qilindi!", call.message.chat.id, call.message.message_id, parse_mode='HTML')

# --- Foydalanuvchiga Premium berish (ID orqali yozish) ---
@bot.callback_query_handler(func=lambda call: call.data == "make_user_prem")
def prem_user_ask(call):
    msg = bot.send_message(call.message.chat.id, "👤 <b>Premium bermoqchi bo'lgan foydalanuvchi ID raqamini yuboring:</b>\n(ID-ni statistikadan olishingiz mumkin)", parse_mode='HTML')
    bot.register_next_step_handler(msg, prem_user_exec)

def prem_user_exec(message):
    user_id = message.text
    if not user_id.isdigit():
        return bot.send_message(message.chat.id, "❌ Faqat ID raqamini yuboring!", reply_markup=admin_kb())

    conn, cursor = get_db()
    cursor.execute("UPDATE users SET status = 'premium' WHERE user_id = ?", (user_id,))
    conn.commit()

    bot.send_message(message.chat.id, f"✅ Foydalanuvchi {user_id} muvaffaqiyatli <b>Premium</b> qilindi!", reply_markup=admin_kb(), parse_mode='HTML')
    # Foydalanuvchining o'ziga ham xabar yuboramiz
    try:
        bot.send_message(user_id, "🎉 <b>Tabriklaymiz! Admin sizga Premium statusini berdi!</b>\nEndi barcha animelar siz uchun ochiq.", parse_mode='HTML')
    except: pass
import datetime
# ==========================================================
# 12. FOYDALANUVCHIGA XABAR YUBORISH (ADMIN UCHUN)
# ==========================================================

@bot.message_handler(func=lambda m: m.text == "📩 Foydalanuvchiga yozish" and m.from_user.id == ADMIN_ID)
def list_users_for_msg(message):
    send_user_list_page(message.chat.id, 0)

def send_user_list_page(chat_id, offset, message_id=None):
    conn, cursor = get_db()
    # Jami foydalanuvchilar sonini olamiz
    total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    # 10 tadan chiqarish
    users = cursor.execute("SELECT user_id, username FROM users LIMIT 10 OFFSET ?", (offset,)).fetchall()

    if not users:
        return bot.send_message(chat_id, "❌ Bazada foydalanuvchilar topilmadi.")

    markup = types.InlineKeyboardMarkup(row_width=1)
    for u in users:
        # Username bo'lsa username, bo'lmasa ID-ni ko'rsatamiz
        name = f"@{u[1]}" if u[1] else f"ID: {u[0]}"
        markup.add(types.InlineKeyboardButton(f"👤 {name}", callback_data=f"msguser_{u[0]}"))

    # Sahifalash (Orqaga / Keyingisi)
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

# Sahifalarni almashtirish uchun callback
@bot.callback_query_handler(func=lambda call: call.data.startswith('usrs_'))
def user_list_callback(call):
    offset = int(call.data.split('_')[1])
    send_user_list_page(call.message.chat.id, offset, call.message.message_id)

# Foydalanuvchi tanlangandan keyin xabar yozishni so'rash
@bot.callback_query_handler(func=lambda call: call.data.startswith('msguser_'))
def ask_admin_message(call):
    target_id = call.data.split('_')[1]
    # Inline tugmalarni o'chirib, yangi xabar yuboramiz
    bot.delete_message(call.message.chat.id, call.message.message_id)

    msg = bot.send_message(call.message.chat.id,
                           f"📝 <b>ID: {target_id} bo'lgan foydalanuvchiga xabaringizni yozing:</b>\n\n(Bekor qilish uchun tugmani bosing)",
                           reply_markup=cancel_kb(), parse_mode='HTML')
    bot.register_next_step_handler(msg, send_final_msg_to_user, target_id)

def send_final_msg_to_user(message, target_id):
    if message.text == "🚫 Bekor qilish":
        return bot.send_message(message.chat.id, "❌ Bekor qilindi.", reply_markup=admin_kb())

    try:
        # Foydalanuvchiga boradigan xabar formati
        full_msg = f"📩 <b>Admindan xabar keldi:</b>\n\n{message.text}"
        bot.send_message(target_id, full_msg, parse_mode='HTML')

        # Adminga tasdiqlash xabari
        bot.send_message(message.chat.id, f"✅ Xabar (ID: {target_id}) ga muvaffaqiyatli yuborildi!", reply_markup=admin_kb())
        print(f"📧 ADMIN_MSG: {target_id} ga xabar yubordi.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik! Foydalanuvchi botni bloklagan bo'lishi mumkin.\n\n{e}", reply_markup=admin_kb())

# --- ADMINGA MUROJAAT VA LİMİT TIZIMI ---

@bot.message_handler(func=lambda m: m.text == "✍️ Adminga murojaat")
def support_start(message):
    u_id = message.from_user.id
    conn, cursor = get_db()

    # Limitni tekshirish
    now = datetime.datetime.now()
    user_limit = cursor.execute("SELECT last_reset, msg_count FROM support_limits WHERE user_id = ?", (u_id,)).fetchone()

    if user_limit:
        last_reset = datetime.datetime.strptime(user_limit[0], '%Y-%m-%d %H:%M:%S')
        msg_count = user_limit[1] if user_limit[1] is not None else 0

        # Agar 1 soat o'tgan bo'lsa, limitni yangilaymiz
        if (now - last_reset).total_seconds() > 3600:
            cursor.execute("UPDATE support_limits SET last_reset = ?, msg_count = 0 WHERE user_id = ?",
                           (now.strftime('%Y-%m-%d %H:%M:%S'), u_id))
            conn.commit()
            msg_count = 0

    if (msg_count or 0) >= 5:
            diff = 3600 - (now - last_reset).total_seconds()
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

  # Bazadagi limitni oshirish (To'g'rilangan variant)
    cursor.execute("""
        INSERT INTO support_limits (user_id, last_reset, msg_count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id) DO UPDATE SET
        msg_count = IFNULL(msg_count, 0) + 1,
        last_reset = excluded.last_reset
    """, (u_id, now))

    # Agar bu birinchi xabar bo'lsa vaqtni to'g'rilash:
    cursor.execute("UPDATE support_limits SET last_reset = (SELECT last_reset FROM support_limits WHERE user_id = ?) WHERE user_id = ? AND msg_count = 1", (u_id, u_id))
    conn.commit()

    # Adminga yuborish
    admin_text = f"📩 <b>Yangi murojaat!</b>\n\n<b>Kimdan:</b> <a href='tg://user?id={u_id}'>{message.from_user.first_name}</a>\n<b>ID:</b> <code>{u_id}</code>\n\n<b>Xabar:</b> {message.text}"

    # Adminga yuborish (va boshqa adminlar bo'lsa ularga ham)
    bot.send_message(ADMIN_ID, admin_text, parse_mode='HTML')

    bot.send_message(message.chat.id, "✅ <b>Xabaringiz adminga yuborildi!</b>\nTez orada javob qaytaramiz.", reply_markup=main_kb(u_id))
    print(f"📩 MUROJAAT: {u_id} dan xabar keldi.")
    # 13. ZAYAVKA KELGANDA UNI BAZAGA SAQLASH
@bot.chat_join_request_handler()
def handle_join_request(chat_join_request):
    u_id = chat_join_request.from_user.id
    conn, cursor = get_db()
    # Foydalanuvchi zayavka tashlaganini requests jadvaliga yozib qo'yamiz
    cursor.execute("INSERT OR IGNORE INTO requests (user_id) VALUES (?)", (u_id,))
    conn.commit()
    print(f"📩 ZAYAVKA: {u_id} kanalga so'rov yubordi va bazaga yozildi.")

# --- ENG OXIRGI QATORLAR ---
if __name__ == "__main__":
    print("🚀 Bot muvaffaqiyatli ishga tushdi...")
    try:
        bot.infinity_polling(allowed_updates=["message", "callback_query", "chat_join_request"])
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")