import telebot
import sqlite3
import logging
from telebot import types

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Database setup
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            premium INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Bot setup
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
bot = telebot.TeleBot(TOKEN)

# Command to start the bot
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()
    bot.reply_to(message, "Welcome to the Anime Bot!")

# Admin command for broadcasting messages
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if is_admin(message.from_user.id):
        msg = message.text[11:]  # Extract the message to broadcast
        send_broadcast(msg)
        bot.reply_to(message, "Broadcast message sent!")
    else:
        bot.reply_to(message, "You are not authorized to use this command.")

def is_admin(user_id):
    # Replace with your admin user ID
    return user_id == YOUR_ADMIN_ID


def send_broadcast(msg):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users')
    users = cursor.fetchall()
    for user in users:
        try:
            bot.send_message(user[0], msg)
        except Exception as e:
            logging.error(f"Failed to send message to {user[0]}: {e}")
    conn.close()

# Error handling
@bot.error_handler()
def error_handler(update, exception):
    logging.error(f'Update: {update} caused error: {exception}')

# Polling loop
while True:
    try:
        logging.info("Bot polling started.")
        bot.polling(none_stop=True)
    except Exception as e:
        logging.error(f'Error occurred: {e}')
        continue

if __name__ == "__main__":
    init_db()