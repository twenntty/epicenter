import telebot
from telebot import types
import sqlite3

TOKEN = '7253772078:AAGI3pDm0Wc9CL3cIPCWTDpbqcmMnO7qV30'
ADMIN_ID = 558372164

bot = telebot.TeleBot(TOKEN)
admin_state = {}

conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

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


@bot.message_handler(func=lambda msg: msg.text == "📬 Розсилка")
def send_newsletter(message):
    if message.chat.id == ADMIN_ID:
        bot.send_message(ADMIN_ID, "Напишіть текст розсилки, який ви хочете відправити всім підписникам:")
        admin_state[ADMIN_ID] = 'sending_newsletter'


@bot.message_handler(func=lambda msg: admin_state.get(msg.chat.id) == 'sending_newsletter')
def handle_newsletter(message):
    if message.chat.id == ADMIN_ID:
        newsletter_text = message.text
        cursor.execute('SELECT user_id FROM subscribers')
        subscribers = cursor.fetchall()

        for subscriber in subscribers:
            user_id = subscriber[0]
            try:
                bot.send_message(user_id, newsletter_text)
            except Exception as e:
                print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

        bot.send_message(ADMIN_ID, "Розсилка була відправлена всім підписникам.")
        admin_state[ADMIN_ID] = None


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.chat.id
    text = message.text

    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()

    if user and user[2] == 'ordering_cosmetics':
        cursor.execute('INSERT INTO appointments (user_id, username, requested_time, status) VALUES (?, ?, ?, ?)',
                       (user_id, message.from_user.username, text, 'pending'))
        conn.commit()
        cursor.execute('UPDATE users SET action = ? WHERE id = ?', (None, user_id))
        conn.commit()
        bot.send_message(user_id, "Дякуємо за вашу заявку! Адміністратор зв'яжеться з вами найближчим часом.")
        bot.send_message(ADMIN_ID,
                         f"🧴 Нова заявка на покупку косметики:\nКористувач: @{message.from_user.username}\nЗапит: {text}\nКонтакти: @{message.from_user.username}")


@bot.message_handler(commands=['pdecline'])
def decline_appointment(message):
    if message.chat.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        reason = ' '.join(parts[2:]) or 'Без причини'
        cursor.execute('UPDATE appointments SET status = ?, reason = ? WHERE user_id = ? AND status = ?',
                       ('declined', reason, user_id, 'pending'))
        conn.commit()
        bot.send_message(user_id, f"❌ Ваша заявка відхилена. Причина: {reason}")
        bot.send_message(ADMIN_ID, "Заявку відхилено.")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"Помилка: {e}")


@bot.message_handler(commands=['pconfirm'])
def confirm_appointment(message):
    if message.chat.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        cursor.execute('UPDATE appointments SET status = ? WHERE user_id = ? AND status = ?',
                       ('confirmed', user_id, 'pending'))
        conn.commit()
        bot.send_message(user_id, "✅ Ваша заявка підтверджена! Очікуйте на консультацію.")
        bot.send_message(ADMIN_ID, f"Заявка користувача @{user_id} підтверджена.")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"Помилка: {e}")


print("Бот запущено..")
bot.polling(none_stop=True)
