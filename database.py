import sqlite3

class Database:
    def __init__(self, db_name='anidb.sqlite'):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        # Create users table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            premium BOOLEAN DEFAULT FALSE
        )''')

        # Create animes table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS animes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            genre TEXT
        )''')

        # Create episodes table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_id INTEGER,
            title TEXT NOT NULL,
            season INTEGER,
            episode_number INTEGER,
            FOREIGN KEY(anime_id) REFERENCES animes(id)
        )''')

        self.connection.commit()

    def add_user(self, username, password):
        try:
            self.cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            self.connection.commit()
        except sqlite3.IntegrityError:
            print('User already exists.')

    def add_anime(self, title, description, genre):
        self.cursor.execute('INSERT INTO animes (title, description, genre) VALUES (?, ?, ?)', (title, description, genre))
        self.connection.commit()

    def add_episode(self, anime_id, title, season, episode_number):
        self.cursor.execute('INSERT INTO episodes (anime_id, title, season, episode_number) VALUES (?, ?, ?, ?)', (anime_id, title, season, episode_number))
        self.connection.commit()

    def close(self):
        self.connection.close()