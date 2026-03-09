import sqlite3
import logging

class Database:
    def __init__(self, db_name='anidb.sqlite'):
        # check_same_thread=False ko'p oqimli (multithreading) ishlatish uchun zarur
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.create_tables()
        logging.info("Ma'lumotlar bazasi muvaffaqiyatli ulandi.")

    def create_tables(self):
        """Barcha kerakli jadvallarni yaratish"""
        with self.connection:
            # Foydalanuvchilar jadvali
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                is_premium BOOLEAN DEFAULT FALSE,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            # Animelar jadvali
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS animes (
                code TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                img_id TEXT,
                is_premium BOOLEAN DEFAULT FALSE,
                views INTEGER DEFAULT 0
            )''')

            # Epizodlar (Qismlar) jadvali
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anime_code TEXT,
                episode_number INTEGER,
                file_id TEXT,
                FOREIGN KEY(anime_code) REFERENCES animes(code)
            )''')

    # --- FOYDALANUVCHILAR BILAN ISHLASH ---

    def add_user(self, user_id, username):
        """Yangi foydalanuvchini ro'yxatga olish"""
        with self.connection:
            return self.cursor.execute(
                'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', 
                (user_id, username)
            )

    def set_premium(self, user_id, status=True):
        """Foydalanuvchiga Premium berish yoki olib qo'yish"""
        with self.connection:
            return self.cursor.execute(
                'UPDATE users SET is_premium = ? WHERE user_id = ?', 
                (status, user_id)
            )

    def is_premium(self, user_id):
        """Foydalanuvchi Premium ekanligini tekshirish"""
        res = self.cursor.execute(
            'SELECT is_premium FROM users WHERE user_id = ?', 
            (user_id,)
        ).fetchone()
        return bool(res[0]) if res else False

    def get_all_users(self):
        """Barcha foydalanuvchilar ID sini olish (Xabar tarqatish uchun)"""
        return self.cursor.execute('SELECT user_id FROM users').fetchall()

    # --- ANIMELAR BILAN ISHLASH ---

    def add_anime(self, code, title, description, img_id, is_premium=False):
        """Yangi anime qo'shish yoki mavjudini yangilash"""
        with self.connection:
            return self.cursor.execute(
                'INSERT OR REPLACE INTO animes (code, title, description, img_id, is_premium) VALUES (?, ?, ?, ?, ?)', 
                (code, title, description, img_id, is_premium)
            )

    def get_anime(self, code):
        """Kod bo'yicha animeni qidirish"""
        return self.cursor.execute('SELECT * FROM animes WHERE code = ?', (code,)).fetchone()

    # --- EPIZODLAR (QISMLAR) BILAN ISHLASH ---

    def add_episode(self, anime_code, ep_num, file_id):
        """Animega yangi qism (video) qo'shish"""
        with self.connection:
            return self.cursor.execute(
                'INSERT INTO episodes (anime_code, episode_number, file_id) VALUES (?, ?, ?)', 
                (anime_code, ep_num, file_id)
            )

    def get_episodes(self, anime_code):
        """Animening barcha qismlarini tartib bilan olish"""
        return self.cursor.execute(
            'SELECT episode_number, file_id FROM episodes WHERE anime_code = ? ORDER BY episode_number ASC', 
            (anime_code,)
        ).fetchall()

    def close(self):
        """Ulanishni yopish"""
        self.connection.close()
