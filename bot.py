import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3

# ========== КОНФИГ ==========
BOT_TOKEN = "8648048022:AAGJM4f3y4rQrxsedYh9hWVx3tnW6DTDO4Y"
ADMIN_IDS = [7810887250, 8779720254]
ADMIN_CODE = "Пор343454543232"
PRIVATE_CHANNEL_LINK = "https://t.me/+SN8uFabakOQ1N2Zh"
PRIVATE_CHANNEL_ID = "-1003837295009"  # Для проверки подписки нужен username или ID
CARD_NUMBER = "2200 3803 0239 4937"

# ========== СОСТОЯНИЯ FSM ==========
class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_video = State()
    waiting_for_photo = State()
    waiting_for_admin_code = State()

class PaymentStates(StatesGroup):
    waiting_for_payment_confirm = State()

# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    
    # Таблица пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            videos_bought TEXT DEFAULT '',
            photos_bought TEXT DEFAULT '',
            total_videos_bought INTEGER DEFAULT 0,
            total_photos_bought INTEGER DEFAULT 0,
            total_diamonds_bought INTEGER DEFAULT 0,
            total_diamonds_spent INTEGER DEFAULT 0,
            total_money_spent INTEGER DEFAULT 0,
            premium_video BOOLEAN DEFAULT 0,
            joined_date TEXT
        )
    ''')
    
    # Таблица очереди видео
    cur.execute('''
        CREATE TABLE IF NOT EXISTS videos_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT,
            added_date TEXT
        )
    ''')
    
    # Таблица очереди фото
    cur.execute('''
        CREATE TABLE IF NOT EXISTS photos_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT,
            added_date TEXT
        )
    ''')
    
    # Таблица покупок (история)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            item_type TEXT,
            amount INTEGER,
            price INTEGER,
            date TEXT,
            confirmed BOOLEAN DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_user(user_id):
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cur.fetchone()
    conn.close()
    return user

def create_user(user_id, username):
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO users (user_id, username, joined_date)
        VALUES (?, ?, ?)
    ''', (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_next_video():
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('SELECT id, file_id FROM videos_queue ORDER BY id ASC LIMIT 1')
    video = cur.fetchone()
    conn.close()
    return video

def remove_video(video_id):
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM videos_queue WHERE id = ?', (video_id,))
    conn.commit()
    conn.close()

def add_video(file_id):
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO videos_queue (file_id, added_date) VALUES (?, ?)', 
                (file_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_next_photo():
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('SELECT id, file_id FROM photos_queue ORDER BY id ASC LIMIT 1')
    photo = cur.fetchone()
    conn.close()
    return photo

def remove_photo(photo_id):
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM photos_queue WHERE id = ?', (photo_id,))
    conn.commit()
    conn.close()

def add_photo(file_id):
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO photos_queue (file_id, added_date) VALUES (?, ?)', 
                (file_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def mark_video_bought(user_id, video_index):
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('UPDATE users SET videos_bought = ?, total_videos_bought = total_videos_bought + 1 WHERE user_id = ?', 
                (video_index, user_id))
    conn.commit()
    conn.close()

def mark_photo_bought(user_id, photo_index):
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('UPDATE users SET photos_bought = ?, total_photos_bought = total_photos_bought + 1 WHERE user_id = ?', 
                (photo_index, user_id))
    conn.commit()
    conn.close()

def add_purchase(user_id, username, item_type, amount, price):
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO purchases (user_id, username, item_type, amount, price, date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, username, item_type, amount, price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    purchase_id = cur.lastrowid
    conn.close()
    return purchase_id

def confirm_purchase(purchase_id):
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('SELECT user_id, item_type, amount, price FROM purchases WHERE id = ?', (purchase_id,))
    purchase = cur.fetchone()
    if purchase:
        user_id, item_type, amount, price = purchase
        if item_type == 'diamonds':
            update_balance(user_id, amount)
            cur.execute('UPDATE users SET total_diamonds_bought = total_diamonds_bought + ?, total_money_spent = total_money_spent + ? WHERE user_id = ?', 
                        (amount, price, user_id))
        elif item_type == 'premium':
            cur.execute('UPDATE users SET premium_video = 1 WHERE user_id = ?', (user_id,))
            cur.execute('UPDATE users SET total_money_spent = total_money_spent + ? WHERE user_id = ?', (price, user_id))
        cur.execute('UPDATE purchases SET confirmed = 1 WHERE id = ?', (purchase_id,))
        conn.commit()
        conn.close()
        return purchase
    conn.close()
    return None

def get_unconfirmed_purchases():
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('SELECT id, user_id, username, item_type, amount, price FROM purchases WHERE confirmed = 0')
    purchases = cur.fetchall()
    conn.close()
    return purchases

def get_all_users():
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM users')
    users = cur.fetchall()
    conn.close()
    return users

def get_statistics():
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users')
    total_users = cur.fetchone()[0]
    cur.execute('SELECT SUM(total_videos_bought) FROM users')
    total_videos = cur.fetchone()[0] or 0
    cur.execute('SELECT SUM(total_photos_bought) FROM users')
    total_photos = cur.fetchone()[0] or 0
    cur.execute('SELECT SUM(total_diamonds_bought) FROM users')
    total_diamonds_bought = cur.fetchone()[0] or 0
    cur.execute('SELECT SUM(total_money_spent) FROM users')
    total_money = cur.fetchone()[0] or 0
    cur.execute('SELECT COUNT(*) FROM users WHERE premium_video = 1')
    total_premium = cur.fetchone()[0] or 0
    conn.close()
    return total_users, total_videos, total_photos, total_diamonds_bought, total_money, total_premium

def get_user_purchases(user_id):
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('SELECT total_videos_bought, total_photos_bought, total_diamonds_bought, total_diamonds_spent, total_money_spent, premium_video FROM users WHERE user_id = ?', (user_id,))
    data = cur.fetchone()
    conn.close()
    return data

def check_subscription(user_id):
    """Проверка подписки на канал (упрощённая, без реального API)"""
    # В реальном коде нужно использовать bot.get_chat_member()
    # Пока возвращаем True для теста
    return True

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard(is_admin=False):
    buttons = [
        [KeyboardButton(text="📱 Смотреть видео"), KeyboardButton(text="🖼 Смотреть фото")],
        [KeyboardButton(text="💎 Купить алмазы"), KeyboardButton(text="🔒 Приватный канал")],
        [KeyboardButton(text="❓ Поддержка"), KeyboardButton(text="👤 Профиль")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="⚙ Админ панель")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_admin_keyboard():
    buttons = [
        [KeyboardButton(text="📢 Обявить"), KeyboardButton(text="📦 Покупки")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="➕ Добавить контент")],
        [KeyboardButton(text="🔙 В главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_add_content_keyboard():
    buttons = [
        [KeyboardButton(text="🎥 Добавить видео"), KeyboardButton(text="🖼 Добавить фото")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ========== ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Проверка подписки
    if not check_subscription(user_id):
        await message.answer(
            f"📌 Здравствуйте, @{username} ❄️\n\n"
            f"🔒 Для использования бота необходимо подписаться на приватный канал:\n\n"
            f"{PRIVATE_CHANNEL_LINK}\n\n"
            f"После подписки нажмите «✅ Я подписался»",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="✅ Я подписался")]],
                resize_keyboard=True
            )
        )
        return
    
    # Регистрация пользователя
    if not get_user(user_id):
        create_user(user_id, username)
    
    user = get_user(user_id)
    is_admin = user_id in ADMIN_IDS
    
    await message.answer(
        f"📌 Здравствуйте, @{username} ❄️\n\n"
        f"💰 Баланс: {user[2]} алмазов\n"
        f"🎥 Куплено видео: {user[5]}/?\n"
        f"🖼 Куплено фото: {user[6]}/?",
        reply_markup=get_main_keyboard(is_admin)
    )

@dp.message(lambda msg: msg.text == "✅ Я подписался")
async def check_subscription_button(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    if check_subscription(user_id):
        if not get_user(user_id):
            create_user(user_id, username)
        user = get_user(user_id)
        is_admin = user_id in ADMIN_IDS
        await message.answer(
            f"✅ Спасибо! Теперь вы можете пользоваться ботом.\n\n"
            f"📌 Здравствуйте, @{username} ❄️\n\n"
            f"💰 Баланс: {user[2]} алмазов\n"
            f"🎥 Куплено видео: {user[5]}/?\n"
            f"🖼 Куплено фото: {user[6]}/?",
            reply_markup=get_main_keyboard(is_admin)
        )
    else:
        await message.answer(
            f"❌ Вы не подписались на канал.\n\n"
            f"Пожалуйста, подпишитесь по ссылке и нажмите кнопку снова:\n\n"
            f"{PRIVATE_CHANNEL_LINK}",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="✅ Я подписался")]],
                resize_keyboard=True
            )
        )

@dp.message(lambda msg: msg.text == "📱 Смотреть видео")
async def watch_video(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.answer("❌ Ошибка. Напишите /start")
        return
    
    # Проверка премиум акции
    if user[11]:  # premium_video
        await message.answer("✅ Вы приобрели все доступные видео!")
        return
    
    # Проверка очереди видео
    video = get_next_video()
    if not video:
        await message.answer("📌 Смотреть видео\n\n✅ Вы приобрели все доступные видео!")
        return
    
    await message.answer(
        f"📌 Смотреть видео\n\n"
        f"Стоимость: 3 алмаза 💎\n"
        f"Ваш баланс: {user[2]} алмазов",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Купить"), KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(lambda msg: msg.text == "🖼 Смотреть фото")
async def watch_photo(message: types.Message):
    await message.answer(
        "🥀 Это ещё не готово. Смотрите видео — видео лучше, чем фотографии!",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Смотреть видео"), KeyboardButton(text="🔙 В главное меню")]],
            resize_keyboard=True
        )
    )

@dp.message(lambda msg: msg.text == "✅ Купить")
async def buy_video(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.answer("❌ Ошибка. Напишите /start")
        return
    
    if user[11]:  # premium_video
        await message.answer("✅ Вы уже купили все видео!")
        return
    
    if user[2] < 3:
        await message.answer(
            "❗ Недостаточно алмазов 💎\n"
            "Купите алмазы в магазине",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="💎 Купить алмазы"), KeyboardButton(text="🔙 Назад")]],
                resize_keyboard=True
            )
        )
        return
    
    video = get_next_video()
    if not video:
        await message.answer("✅ Вы приобрели все доступные видео!")
        return
    
    # Списываем алмазы
    update_balance(user_id, -3)
    # Отправляем видео
    await bot.send_video(chat_id=user_id, video=video[1])
    # Удаляем видео из очереди
    remove_video(video[0])
    # Обновляем статистику пользователя
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('UPDATE users SET total_videos_bought = total_videos_bought + 1, total_diamonds_spent = total_diamonds_spent + 3 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    new_balance = user[2] - 3
    await message.answer(
        f"🎥 Видео куплено!\n\n"
        f"💰 Ваш баланс: {new_balance} алмазов\n"
        f"Стоимость: 3 алмаза",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Смотреть ещё"), KeyboardButton(text="🔙 В главное меню")]],
            resize_keyboard=True
        )
    )

@dp.message(lambda msg: msg.text == "📱 Смотреть ещё")
async def watch_more(message: types.Message):
    await watch_video(message)

@dp.message(lambda msg: msg.text == "💎 Купить алмазы")
async def buy_diamonds(message: types.Message):
    buttons = [
        [KeyboardButton(text="10💎 - 15₽"), KeyboardButton(text="50💎 - 100₽")],
        [KeyboardButton(text="500💎 - 500₽"), KeyboardButton(text="1000💎 - 1000₽")],
        [KeyboardButton(text="🌟 Премиум акция"), KeyboardButton(text="🔙 Назад")]
    ]
    await message.answer(
        "💎 Покупай алмазы! 💎\n\n"
        "500 💎 — самое выгодное ❗\n\n"
        "🔹 10 💎 — 15 ₽\n"
        "🔹 50 💎 — 100 ₽\n"
        "🔹 500 💎 — 500 ₽\n"
        "🔹 1000 💎 — 1000 ₽\n\n"
        "🌟 Премиум акция (нажмите для подробностей)",
        reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    )

@dp.message(lambda msg: msg.text in ["10💎 - 15₽", "50💎 - 100₽", "500💎 - 500₽", "1000💎 - 1000₽"])
async def select_diamond_package(message: types.Message):
    packages = {
        "10💎 - 15₽": (10, 15),
        "50💎 - 100₽": (50, 100),
        "500💎 - 500₽": (500, 500),
        "1000💎 - 1000₽": (1000, 1000)
    }
    diamonds, price = packages[message.text]
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Сохраняем покупку
    purchase_id = add_purchase(user_id, username, 'diamonds', diamonds, price)
    
    await message.answer(
        f"✅ Вы выбрали 💎\n\n"
        f"Количество: {diamonds} алмазов\n"
        f"Стоимость: {price} ₽\n\n"
        f"💳 Перевод на карту:\n{CARD_NUMBER}\n\n"
        f"👇 После перевода нажми 👇",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Я оплатил товар ✅"), KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(lambda msg: msg.text == "🌟 Премиум акция")
async def premium_action(message: types.Message):
    await message.answer(
        "🌟 Премиум акция 🌟\n\n"
        "250 ₽ — все видео 📌\n\n"
        "При покупке акции вы получаете доступ ко всем видео "
        "без необходимости тратить алмазы.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Купить акцию"), KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(lambda msg: msg.text == "✅ Купить акцию")
async def buy_premium_action(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    purchase_id = add_purchase(user_id, username, 'premium', 0, 250)
    
    await message.answer(
        f"✅ Вы выбрали Премиум акцию\n\n"
        f"Стоимость: 250 ₽\n\n"
        f"💳 Перевод на карту:\n{CARD_NUMBER}\n\n"
        f"👇 После перевода нажми 👇",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Я оплатил товар ✅"), KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(lambda msg: msg.text == "✅ Я оплатил товар ✅")
async def confirm_payment(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Отправляем админам уведомление
    for admin_id in ADMIN_IDS:
        await bot.send_message(
            admin_id,
            f"❗ НОВАЯ ПОКУПКА ❗\n\n"
            f"Пользователь: @{username} | ID: {user_id}\n"
            f"Ожидает подтверждения.\n\n"
            f"Проверьте историю покупок в админ-панели."
        )
    
    await message.answer(
        "✅ Заявка отправлена! После проверки админом алмазы будут начислены.\n\n"
        "Обычно это занимает несколько минут.",
        reply_markup=get_main_keyboard(message.from_user.id in ADMIN_IDS)
    )

@dp.message(lambda msg: msg.text == "🔒 Приватный канал")
async def private_channel(message: types.Message):
    await message.answer(
        f"📌 Приватный канал\n\n"
        f"Подпишитесь, чтобы смотреть контент:\n\n"
        f"{PRIVATE_CHANNEL_LINK}\n\n"
        f"После подписки нажмите «✅ Я подписался»",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Я подписался"), KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(lambda msg: msg.text == "👤 Профиль")
async def profile(message: types.Message):
    user_id = message.from_user.id
    data = get_user_purchases(user_id)
    
    if not data:
        await message.answer("❌ Ошибка. Напишите /start")
        return
    
    videos, photos, diamonds_bought, diamonds_spent, money_spent, premium = data
    
    await message.answer(
        f"👥 Ваш профиль\n\n"
        f"🎥 Куплено видео: {videos} / ?\n"
        f"🖼 Куплено фото: {photos} / ?\n"
        f"💎 Куплено алмазов (всего): {diamonds_bought} шт.\n"
        f"💸 Потрачено алмазов (всего): {diamonds_spent} шт.\n"
        f"💰 Потрачено денег (всего): {money_spent} ₽\n"
        f"🌟 Премиум акция: {'Есть' if premium else 'Нет'}",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(lambda msg: msg.text == "❓ Поддержка")
async def support(message: types.Message):
    await message.answer(
        "❗ Ко всем вопросам 📩\n\n"
        "👨‍💼 Менеджер: @SkweezyEr\n\n"
        "Ссылка: t.me/SkweezyEr",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(lambda msg: msg.text == "⚙ Админ панель")
async def admin_panel(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id in ADMIN_IDS:
        await message.answer(
            f"📌 Здравствуйте, {message.from_user.username}",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            "🔐 Введите код админа:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔙 Назад")]],
                resize_keyboard=True
            )
        )
        await state.set_state(AdminStates.waiting_for_admin_code)

@dp.message(AdminStates.waiting_for_admin_code)
async def check_admin_code(message: types.Message, state: FSMContext):
    if message.text == ADMIN_CODE:
        await message.answer(
            f"📌 Здравствуйте, {message.from_user.username}",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer("❌ Неверный код доступа.")
    await state.clear()

@dp.message(lambda msg: msg.text == "📢 Обявить")
async def broadcast(message: types.Message, state: FSMContext):
    await message.answer(
        "📌 Выбрано обявить\n\n"
        "Напишите текст для рассылки 👇",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )
    await state.set_state(AdminStates.waiting_for_broadcast)

@dp.message(AdminStates.waiting_for_broadcast)
async def send_broadcast(message: types.Message, state: FSMContext):
    text = message.text
    users = get_all_users()
    sent = 0
    
    for user in users:
        try:
            await bot.send_message(user[0], text)
            sent += 1
        except:
            pass
    
    await message.answer(
        f"✅ Сообщение отправлено пользователям!\n\n"
        f"Отправлено: {sent} пользователям",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

@dp.message(lambda msg: msg.text == "📦 Покупки")
async def view_purchases(message: types.Message):
    purchases = get_unconfirmed_purchases()
    
    if not purchases:
        await message.answer(
            "💳 Покупки\n\n"
            "Нет ожидающих подтверждения покупок.",
            reply_markup=get_admin_keyboard()
        )
        return
    
    text = "💳 Ожидают подтверждения:\n\n"
    for p in purchases:
        purchase_id, user_id, username, item_type, amount, price = p
        if item_type == 'diamonds':
            text += f"{purchase_id}. @{username} | {amount}💎 | {price}₽\n"
        elif item_type == 'premium':
            text += f"{purchase_id}. @{username} | Премиум акция | {price}₽\n"
    
    text += f"\nДля подтверждения отправьте ID покупки командой:\n/confirm {purchase_id}"
    
    await message.answer(text, reply_markup=get_admin_keyboard())

@dp.message(lambda msg: msg.text == "📊 Статистика")
async def view_statistics(message: types.Message):
    total_users, total_videos, total_photos, total_diamonds, total_money, total_premium = get_statistics()
    
    await message.answer(
        f"📊 Статистика\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🎥 Куплено видео (всего): {total_videos}\n"
        f"🖼 Куплено фото (всего): {total_photos}\n"
        f"💎 Продано алмазов: {total_diamonds} шт.\n"
        f"💰 На сумму: {total_money} ₽\n"
        f"🌟 Премиум акций продано: {total_premium}",
        reply_markup=get_admin_keyboard()
    )

@dp.message(lambda msg: msg.text == "➕ Добавить контент")
async def add_content(message: types.Message):
    await message.answer(
        "➕ Добавить контент\n\n"
        "Что вы хотите добавить?",
        reply_markup=get_add_content_keyboard()
    )

@dp.message(lambda msg: msg.text == "🎥 Добавить видео")
async def add_video_content(message: types.Message, state: FSMContext):
    await message.answer(
        "📌 Отправьте видео:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )
    await state.set_state(AdminStates.waiting_for_video)

@dp.message(AdminStates.waiting_for_video, F.video)
async def save_video(message: types.Message, state: FSMContext):
    file_id = message.video.file_id
    add_video(file_id)
    
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM videos_queue')
    count = cur.fetchone()[0]
    conn.close()
    
    await message.answer(
        f"✅ Видео добавлено!\n\n"
        f"Всего видео в очереди: {count}",
        reply_markup=get_add_content_keyboard()
    )
    await state.clear()

@dp.message(lambda msg: msg.text == "🖼 Добавить фото")
async def add_photo_content(message: types.Message, state: FSMContext):
    await message.answer(
        "📌 Отправьте фото:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )
    await state.set_state(AdminStates.waiting_for_photo)

@dp.message(AdminStates.waiting_for_photo, F.photo)
async def save_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    add_photo(file_id)
    
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM photos_queue')
    count = cur.fetchone()[0]
    conn.close()
    
    await message.answer(
        f"✅ Фото добавлено!\n\n"
        f"Всего фото в очереди: {count}",
        reply_markup=get_add_content_keyboard()
    )
    await state.clear()

@dp.message(lambda msg: msg.text == "🔙 Назад")
async def back_button(message: types.Message):
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    await message.answer(
        "Главное меню",
        reply_markup=get_main_keyboard(is_admin)
    )

@dp.message(lambda msg: msg.text == "🔙 В главное меню")
async def back_to_main(message: types.Message):
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    await message.answer(
        "Главное меню",
        reply_markup=get_main_keyboard(is_admin)
    )

@dp.message(Command("confirm"))
async def confirm_purchase_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❗ не админ")
        return
    
    try:
        purchase_id = int(message.text.split()[1])
        purchase = confirm_purchase(purchase_id)
        
        if purchase:
            user_id, item_type, amount, price = purchase
            user = get_user(user_id)
            
            if item_type == 'diamonds':
                await bot.send_message(
                    user_id,
                    f"❗ ЗАКАЗ ОДОБРЕН ❗\n\n"
                    f"Вам начислено {amount} алмазов 💎\n\n"
                    f"💰 Ваш баланс: {user[2] + amount} алмазов",
                    reply_markup=get_main_keyboard(False)
                )
                await message.answer(f"✅ Покупка {purchase_id} подтверждена. Пользователю начислено {amount} алмазов.")
            elif item_type == 'premium':
                await bot.send_message(
                    user_id,
                    f"❗ ЗАКАЗ ОДОБРЕН ❗\n\n"
                    f"Вам открыт доступ ко всем видео! 🌟\n\n"
                    f"[📱 Смотреть видео]",
                    reply_markup=get_main_keyboard(False)
                )
                await message.answer(f"✅ Покупка {purchase_id} подтверждена. Пользователю открыт доступ ко всем видео.")
        else:
            await message.answer("❌ Покупка не найдена или уже подтверждена.")
    except:
        await message.answer("❌ Используйте: /confirm [ID покупки]")

# ========== ЗАПУСК ==========
async def main():
    init_db()
    
    # Добавляем тестовые видео и фото, если их нет
    conn = sqlite3.connect('strech_bot.db')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM videos_queue')
    if cur.fetchone()[0] == 0:
        # Здесь нужно добавить реальные file_id видео
        pass
    cur.execute('SELECT COUNT(*) FROM photos_queue')
    if cur.fetchone()[0] == 0:
        # Здесь нужно добавить реальные file_id фото
        pass
    conn.close()
    
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())