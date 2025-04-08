import os
import telebot
from telebot import types
from aiohttp import web
import sqlite3
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота и ID администратора
TOKEN = '7253772078:AAGI3pDm0Wc9CL3cIPCWTDpbqcmMnO7qV30'
ADMIN_ID = 558372164

bot = telebot.TeleBot(TOKEN)
admin_state = {}

# Создание подключения к базе данных SQLite
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

# Создаем приложение aiohttp
app = web.Application()


# Обработчик для получения вебхуков от Telegram
async def handle(request):
    json_str = await request.text()
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return web.Response(text='OK')


app.router.add_post(f'/{TOKEN}', handle)


# Устанавливаем вебхук
def set_webhook():
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip('/')
    if not render_url.startswith("https://"):
        render_url = f"https://{render_url}"
    webhook_url = f"{render_url}/{TOKEN}"
    logger.info(f"Установка вебхука: {webhook_url}")
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)


# Обработчики команд и кнопок
@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = message.chat.id
    username = message.from_user.username
    cursor.execute('INSERT OR REPLACE INTO users (id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        types.KeyboardButton("🧴 Замовити косметику"),
        types.KeyboardButton("💬 Консультація"),
        types.KeyboardButton("📬 Розсилка"),
        types.KeyboardButton("🗕️ Запис на прийом"),
        types.KeyboardButton("🔔 Підписатися на розсилку"),
        types.KeyboardButton("❌ Відписатися від розсилки")
    ]

    if user_id == ADMIN_ID:
        buttons.append(types.KeyboardButton("/admin"))

    markup.add(*buttons)
    bot.send_message(user_id, "Вітаю в боті Епіцентр! Оберіть дію:", reply_markup=markup)


@bot.message_handler(func=lambda msg: msg.text == "🧴 Замовити косметику")
def order_cosmetics(message):
    user_id = message.chat.id
    cursor.execute('UPDATE users SET action = ? WHERE id = ?', ('ordering_cosmetics', user_id))
    conn.commit()
    bot.send_message(user_id, "Будь ласка, введіть назву косметики, яку ви хочете замовити:")


@bot.message_handler(func=lambda msg: msg.text == "💬 Консультація")
def request_consultation(message):
    user_id = message.chat.id
    bot.send_message(user_id,
                     "Для отримання консультації, будь ласка, зв'яжіться з нашим менеджером: @manager_username")


@bot.message_handler(func=lambda msg: msg.text == "🗕️ Запис на прийом")
def book_appointment(message):
    user_id = message.chat.id
    cursor.execute('UPDATE users SET action = ? WHERE id = ?', ('booking_appointment', user_id))
    conn.commit()
    bot.send_message(user_id, "Будь ласка, введіть бажану дату та час для запису на прийом:")


@bot.message_handler(func=lambda msg: msg.text == "🔔 Підписатися на розсилку")
def subscribe(message):
    user_id = message.chat.id
    cursor.execute('INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)', (user_id,))
    conn.commit()
    bot.send_message(user_id,
                     "Ви успішно підписались на розсилку! Ви будете отримувати актуальні новини та пропозиції.")


@bot.message_handler(func=lambda msg: msg.text == "❌ Відписатися від розсилки")
def unsubscribe(message):
    user_id = message.chat.id
    cursor.execute('DELETE FROM subscribers WHERE user_id = ?', (user_id,))
    conn.commit()
    bot.send_message(user_id, "Ви успішно відписались від розсилки.")


@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("📊 Статистика")
        btn2 = types.KeyboardButton("📬 Розсилка")
        btn3 = types.KeyboardButton("↩️ На головну")
        markup.add(btn1, btn2, btn3)
        bot.send_message(ADMIN_ID, "Панель адміністратора:", reply_markup=markup)


@bot.message_handler(func=lambda msg: msg.text == "↩️ На головну")
def back_to_main(message):
    welcome(message)


@bot.message_handler(func=lambda msg: msg.text == "📊 Статистика")
def show_stats(message):
    if message.chat.id == ADMIN_ID:
        cursor.execute('SELECT COUNT(*) FROM users')
        users_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM subscribers')
        subs_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM appointments WHERE status = "pending"')
        pending_appointments = cursor.fetchone()[0]

        stats = (
            f"📊 Статистика бота:\n\n"
            f"👥 Користувачів: {users_count}\n"
            f"🔔 Підписників: {subs_count}\n"
            f"⏳ Очікують обробки: {pending_appointments}"
        )

        bot.send_message(ADMIN_ID, stats)


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

        success = 0
        failed = 0

        for subscriber in subscribers:
            user_id = subscriber[0]
            try:
                bot.send_message(user_id, newsletter_text)
                success += 1
            except Exception as e:
                logger.error(f"Не вдалося відправити повідомлення {user_id}: {e}")
                failed += 1

        bot.send_message(ADMIN_ID, f"Розсилка завершена:\nУспішно: {success}\nНе вдалося: {failed}")
        admin_state[ADMIN_ID] = None


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.chat.id
    cursor.execute('SELECT action FROM users WHERE id = ?', (user_id,))
    user_action = cursor.fetchone()

    if user_action and user_action[0] == 'ordering_cosmetics':
        cursor.execute('INSERT INTO appointments (user_id, username, requested_time, status) VALUES (?, ?, ?, ?)',
                       (user_id, message.from_user.username, message.text, 'pending'))
        conn.commit()
        cursor.execute('UPDATE users SET action = ? WHERE id = ?', (None, user_id))
        conn.commit()
        bot.send_message(user_id, "Дякуємо за ваше замовлення! Ми зв'яжемося з вами найближчим часом.")
        bot.send_message(ADMIN_ID, f"🧴 Новий запит на косметику від @{message.from_user.username}:\n{message.text}")

    elif user_action and user_action[0] == 'booking_appointment':
        cursor.execute('INSERT INTO appointments (user_id, username, requested_time, status) VALUES (?, ?, ?, ?)',
                       (user_id, message.from_user.username, message.text, 'pending'))
        conn.commit()
        cursor.execute('UPDATE users SET action = ? WHERE id = ?', (None, user_id))
        conn.commit()
        bot.send_message(user_id, "Дякуємо за запис! Ми підтвердимо вашу дату та час найближчим часом.")
        bot.send_message(ADMIN_ID, f"🗓 Новий запис від @{message.from_user.username}:\n{message.text}")


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
        bot.send_message(user_id, "✅ Ваша заявка підтверджена! Очікуйте на дзвінок.")
        bot.send_message(ADMIN_ID, f"Заявка користувача {user_id} підтверджена.")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"Помилка: {e}")



if __name__ == '__main__':
    set_webhook()
    web.run_app(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))