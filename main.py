import os
import telebot
from telebot import types
import sqlite3
from flask import Flask, request
import threading

# Настройки
TOKEN = '7253772078:AAGI3pDm0Wc9CL3cIPCWTDpbqcmMnO7qV30'
ADMIN_ID = 558372164

bot = telebot.TeleBot(TOKEN)
admin_state = {}

# Создание подключения к базе данных
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц в базе данных
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                      id INTEGER PRIMARY KEY,
                      username TEXT,
                      action TEXT
                  )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS appointments (
                      user_id INTEGER,
                      username TEXT,
                      requested_time TEXT,
                      status TEXT,
                      reason TEXT
                  )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS subscribers (
                      user_id INTEGER PRIMARY KEY
                  )''')
conn.commit()

# Flask сервер для прослушивания порта
app = Flask(__name__)

@app.route('/')
def webhook():
    return "Telegram Bot is running!"

@app.route(f'/{TOKEN}', methods=['POST'])
def get_message():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return 'OK', 200

# Устанавливаем вебхук
def set_webhook():
    webhook_url = f'https://{os.environ["RENDER_EXTERNAL_URL"]}/{TOKEN}'
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)

# Обработка команд и сообщений в Telegram-боте
@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = message.chat.id
    username = message.from_user.username
    cursor.execute('INSERT OR REPLACE INTO users (id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🧴 Замовити косметику")
    btn2 = types.KeyboardButton("💬 Консультація")
    btn3 = types.KeyboardButton("📬 Розсилка")
    btn4 = types.KeyboardButton("🗕️ Запис на прийом")
    btn5 = types.KeyboardButton("🔔 Підписатися на розсилку")
    btn6 = types.KeyboardButton("❌ Відписатися від розсилки")

    if user_id == ADMIN_ID:
        btn7 = types.KeyboardButton("/admin")
        markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
    else:
        markup.add(btn1, btn2, btn3, btn4, btn5, btn6)

    bot.send_message(user_id, "Вітаю в боті Епіцентр! Оберіть дію:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "🔔 Підписатися на розсилку")
def subscribe(message):
    user_id = message.chat.id
    cursor.execute('INSERT OR REPLACE INTO subscribers (user_id) VALUES (?)', (user_id,))
    conn.commit()
    bot.send_message(user_id, "Ви підписалися на розсилку! Ви будете отримувати новини та оновлення.")

@bot.message_handler(func=lambda msg: msg.text == "❌ Відписатися від розсилки")
def unsubscribe(message):
    user_id = message.chat.id
    cursor.execute('DELETE FROM subscribers WHERE user_id = ?', (user_id,))
    conn.commit()
    bot.send_message(user_id, "Ви відписалися від розсилки. Ви більше не будете отримувати новини.")

# Другие обработчики команд Telegram-бота...

# Запуск Flask сервера в отдельном потоке
def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

# Запуск бота и Flask сервера
if __name__ == '__main__':
    # Настройка вебхука
    set_webhook()

    # Запуск Flask сервера в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Запуск Telegram-бота
    bot.polling(none_stop=True)
