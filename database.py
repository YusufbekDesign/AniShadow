import sqlite3

class Database:
    def __init__(self, db_name='anidb.sqlite'):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        # Foydalanuvchilar jadvali (Telegram ID bilan)
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
            is_premium BOOLEAN DEFAULT FALSE
        )''')

        # Qismlar jadvali (Video file_id bilan)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_code TEXT,
            episode_number INTEGER,
            file_id TEXT,
            FOREIGN KEY(anime_code) REFERENCES animes(code)
        )''')

        self.connection.commit()

    # --- FOYDALANUVCHI AMALLARI ---
    def add_user(self, user_id, username):
        self.cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
        self.connection.commit()

    def set_premium(self, user_id, status=True):
        self.cursor.execute('UPDATE users SET is_premium = ? WHERE user_id = ?', (status, user_id))
        self.connection.commit()

    def is_premium(self, user_id):
        res = self.cursor.execute('SELECT is_premium FROM users WHERE user_id = ?', (user_id,)).fetchone()
        return res[0] if res else False

    # --- ANIME AMALLARI ---
    def add_anime(self, code, title, description, img_id, is_premium=False):
        self.cursor.execute('INSERT OR REPLACE INTO animes VALUES (?, ?, ?, ?, ?)', 
                            (code, title, description, img_id, is_premium))
        self.connection.commit()

    def get_anime(self, code):
        return self.cursor.execute('SELECT * FROM animes WHERE code = ?', (code,)).fetchone()

    # --- EPIZOD AMALLARI ---
    def add_episode(self, anime_code, ep_num, file_id):
        self.cursor.execute('INSERT INTO episodes (anime_code, episode_number, file_id) VALUES (?, ?, ?)', 
                            (anime_code, ep_num, file_id))
        self.connection.commit()

    def get_episodes(self, anime_code):
        return self.cursor.execute('SELECT episode_number, file_id FROM episodes WHERE anime_code = ? ORDER BY episode_number', (anime_code,)).fetchall()

    def close(self):
        self.connection.close()
