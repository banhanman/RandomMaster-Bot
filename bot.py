import random
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import config
from datetime import datetime, timedelta
import json
import os
import pytz

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния бота
class RandomStates(StatesGroup):
    waiting_for_number_range = State()
    waiting_for_list = State()
    waiting_for_names = State()
    waiting_for_teams = State()
    waiting_for_weights = State()
    waiting_for_date_range = State()
    waiting_for_password_length = State()

# Сохраняем историю для пользователей
user_history = {}

def save_user_data(user_id):
    """Сохраняем историю пользователя в файл"""
    if user_id not in user_history:
        return
    
    filename = f"user_data/{user_id}.json"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(user_history[user_id], f, ensure_ascii=False, indent=2)

def load_user_data(user_id):
    """Загружаем историю пользователя из файла"""
    filename = f"user_data/{user_id}.json"
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    # Загружаем историю пользователя
    if user_id not in user_history:
        user_history[user_id] = load_user_data(user_id) or []
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("🎲 Случайное число", callback_data="random_number"),
        InlineKeyboardButton("📋 Случайный выбор", callback_data="random_choice"),
        InlineKeyboardButton("👥 Выбор команды", callback_data="team_chooser"),
        InlineKeyboardButton("🔐 Генератор пароля", callback_data="password_generator"),
        InlineKeyboardButton("🔄 Перемешать список", callback_data="shuffle_list"),
        InlineKeyboardButton("📅 Случайная дата", callback_data="random_date"),
        InlineKeyboardButton("⚖️ Взвешенный выбор", callback_data="weighted_choice"),
        InlineKeyboardButton("📜 История", callback_data="show_history"),
        InlineKeyboardButton("❓ Помощь", callback_data="help_info")
    ]
    keyboard.add(*buttons)
    
    await message.answer(
        "🎲 Добро пожаловать в RandomMaster Bot!\n\n"
        "Я помогу вам сделать случайный выбор в любой ситуации:\n"
        "• Случайные числа\n"
        "• Выбор из списка\n"
        "• Разделение на команды\n"
        "• Генерация паролей\n"
        "• Случайные даты\n"
        "• Взвешенный выбор\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == 'random_number')
async def random_number_handler(callback_query: types.CallbackQuery):
    await bot.send_message(
        callback_query.from_user.id,
        "🔢 Введите диапазон чисел в формате:\n\n"
        "<code>от до</code>\n\n"
        "Пример: <code>1 100</code>\n"
        "Пример: <code>-10 10</code>",
        parse_mode="HTML"
    )
    await RandomStates.waiting_for_number_range.set()

@dp.message_handler(state=RandomStates.waiting_for_number_range)
async def process_number_range(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    
    try:
        parts = text.split()
        if len(parts) != 2:
            raise ValueError("Неправильный формат")
        
        min_val = int(parts[0])
        max_val = int(parts[1])
        
        if min_val >= max_val:
            raise ValueError("Минимум должен быть меньше максимума")
        
        result = random.randint(min_val, max_val)
        
        # Сохраняем в историю
        history_entry = {
            "type": "number",
            "input": f"{min_val}-{max_val}",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        user_history[user_id].append(history_entry)
        save_user_data(user_id)
        
        await message.answer(f"🎲 Случайное число: <b>{result}</b>", parse_mode="HTML")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}\nПопробуйте еще раз в формате: <code>от до</code>", parse_mode="HTML")
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'random_choice')
async def random_choice_handler(callback_query: types.CallbackQuery):
    await bot.send_message(
        callback_query.from_user.id,
        "📝 Введите элементы для выбора, разделяя их запятыми:\n\n"
        "Пример: <code>Яблоко, Груша, Банан, Апельсин</code>\n"
        "Пример: <code>Иван, Мария, Пётр, Анна</code>",
        parse_mode="HTML"
    )
    await RandomStates.waiting_for_list.set()

@dp.message_handler(state=RandomStates.waiting_for_list)
async def process_random_choice(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if not text:
        await message.answer("❌ Список не может быть пустым")
        await state.finish()
        return
    
    items = [item.strip() for item in text.split(',') if item.strip()]
    
    if len(items) < 2:
        await message.answer("❌ Нужно минимум 2 элемента для выбора")
        await state.finish()
        return
    
    result = random.choice(items)
    
    # Сохраняем в историю
    history_entry = {
        "type": "choice",
        "input": text,
        "result": result,
        "timestamp": datetime.now().isoformat()
    }
    user_history[user_id].append(history_entry)
    save_user_data(user_id)
    
    await message.answer(f"🎯 Выбран: <b>{result}</b>", parse_mode="HTML")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'team_chooser')
async def team_chooser_handler(callback_query: types.CallbackQuery):
    await bot.send_message(
        callback_query.from_user.id,
        "👥 Введите имена участников, разделяя их запятыми:\n\n"
        "Пример: <code>Алексей, Мария, Иван, Ольга, Дмитрий, Екатерина</code>",
        parse_mode="HTML"
    )
    await RandomStates.waiting_for_names.set()

@dp.message_handler(state=RandomStates.waiting_for_names)
async def process_names(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if not text:
        await message.answer("❌ Список имен не может быть пустым")
        await state.finish()
        return
    
    names = [name.strip() for name in text.split(',') if name.strip()]
    
    if len(names) < 2:
        await message.answer("❌ Нужно минимум 2 участника")
        await state.finish()
        return
    
    # Сохраняем имена в состоянии
    async with state.proxy() as data:
        data['names'] = names
    
    await message.answer(
        "🔢 Введите количество команд (или названия команд через запятую):\n\n"
        "Пример: <code>2</code>\n"
        "Пример: <code>Красные, Синие, Зеленые</code>",
        parse_mode="HTML"
    )
    await RandomStates.waiting_for_teams.set()

@dp.message_handler(state=RandomStates.waiting_for_teams)
async def process_teams(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    
    async with state.proxy() as data:
        names = data['names']
    
    # Определяем команды
    if text.isdigit():
        team_count = int(text)
        if team_count < 2:
            await message.answer("❌ Минимум 2 команды")
            await state.finish()
            return
        
        team_names = [f"Команда {i+1}" for i in range(team_count)]
    else:
        team_names = [name.strip() for name in text.split(',') if name.strip()]
        if len(team_names) < 2:
            await message.answer("❌ Минимум 2 команды")
            await state.finish()
            return
    
    # Перемешиваем имена
    random.shuffle(names)
    
    # Распределяем по командам
    teams = {team: [] for team in team_names}
    for i, name in enumerate(names):
        team = team_names[i % len(team_names)]
        teams[team].append(name)
    
    # Формируем результат
    result = "🏆 Распределение по командам:\n\n"
    for team, members in teams.items():
        result += f"<b>{team}:</b>\n"
        result += "\n".join([f"• {member}" for member in members])
        result += "\n\n"
    
    # Сохраняем в историю
    history_entry = {
        "type": "teams",
        "input": {"names": names, "teams": team_names},
        "result": teams,
        "timestamp": datetime.now().isoformat()
    }
    user_history[user_id].append(history_entry)
    save_user_data(user_id)
    
    await message.answer(result, parse_mode="HTML")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'password_generator')
async def password_generator_handler(callback_query: types.CallbackQuery):
    await bot.send_message(
        callback_query.from_user.id,
        "🔢 Введите длину пароля (от 6 до 50 символов):"
    )
    await RandomStates.waiting_for_password_length.set()

@dp.message_handler(state=RandomStates.waiting_for_password_length)
async def process_password_length(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    
    try:
        length = int(text)
        if length < 6 or length > 50:
            raise ValueError("Длина должна быть от 6 до 50 символов")
        
        # Генерация пароля
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()"
        password = ''.join(random.choice(chars) for _ in range(length))
        
        # Сохраняем в историю
        history_entry = {
            "type": "password",
            "input": length,
            "result": password,
            "timestamp": datetime.now().isoformat()
        }
        user_history[user_id].append(history_entry)
        save_user_data(user_id)
        
        await message.answer(f"🔑 Ваш пароль:\n<code>{password}</code>", parse_mode="HTML")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'shuffle_list')
async def shuffle_list_handler(callback_query: types.CallbackQuery):
    await bot.send_message(
        callback_query.from_user.id,
        "📝 Введите элементы для перемешивания, разделяя их запятыми:\n\n"
        "Пример: <code>1, 2, 3, 4, 5</code>\n"
        "Пример: <code>А, Б, В, Г, Д</code>",
        parse_mode="HTML"
    )
    await RandomStates.waiting_for_list.set()

@dp.callback_query_handler(lambda c: c.data == 'random_date')
async def random_date_handler(callback_query: types.CallbackQuery):
    await bot.send_message(
        callback_query.from_user.id,
        "📅 Введите диапазон дат в формате:\n\n"
        "<code>ГГГГ-ММ-ДД ГГГГ-ММ-ДД</code>\n\n"
        "Пример: <code>2023-01-01 2023-12-31</code>",
        parse_mode="HTML"
    )
    await RandomStates.waiting_for_date_range.set()

@dp.message_handler(state=RandomStates.waiting_for_date_range)
async def process_date_range(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    
    try:
        parts = text.split()
        if len(parts) != 2:
            raise ValueError("Неправильный формат")
        
        start_date = datetime.strptime(parts[0], "%Y-%m-%d")
        end_date = datetime.strptime(parts[1], "%Y-%m-%d")
        
        if start_date >= end_date:
            raise ValueError("Начальная дата должна быть раньше конечной")
        
        # Генерация случайной даты
        time_between = end_date - start_date
        random_days = random.randrange(time_between.days)
        random_date = start_date + timedelta(days=random_days)
        
        # Форматируем дату
        formatted_date = random_date.strftime("%d.%m.%Y")
        
        # Сохраняем в историю
        history_entry = {
            "type": "date",
            "input": f"{parts[0]} - {parts[1]}",
            "result": formatted_date,
            "timestamp": datetime.now().isoformat()
        }
        user_history[user_id].append(history_entry)
        save_user_data(user_id)
        
        await message.answer(f"📅 Случайная дата: <b>{formatted_date}</b>", parse_mode="HTML")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}\nПопробуйте еще раз в формате: <code>ГГГГ-ММ-ДД ГГГГ-ММ-ДД</code>", parse_mode="HTML")
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'weighted_choice')
async def weighted_choice_handler(callback_query: types.CallbackQuery):
    await bot.send_message(
        callback_query.from_user.id,
        "⚖️ Введите элементы и их веса в формате:\n\n"
        "<code>Элемент1:Вес1, Элемент2:Вес2, ...</code>\n\n"
        "Пример: <code>Красный:3, Зеленый:2, Синий:1</code>\n"
        "Пример: <code>Яблоко:5, Груша:3, Банан:2</code>",
        parse_mode="HTML"
    )
    await RandomStates.waiting_for_weights.set()

@dp.message_handler(state=RandomStates.waiting_for_weights)
async def process_weighted_choice(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    
    try:
        items = []
        total_weight = 0
        
        for pair in text.split(','):
            pair = pair.strip()
            if not pair:
                continue
                
            if ':' not in pair:
                raise ValueError(f"Неправильный формат пары: {pair}")
            
            parts = pair.split(':', 1)
            item = parts[0].strip()
            weight = float(parts[1].strip())
            
            if weight <= 0:
                raise ValueError(f"Вес должен быть положительным: {item}")
            
            items.append((item, weight))
            total_weight += weight
        
        if len(items) < 2:
            raise ValueError("Нужно минимум 2 элемента")
        
        # Взвешенный выбор
        rand = random.uniform(0, total_weight)
        current = 0
        for item, weight in items:
            current += weight
            if rand <= current:
                result = item
                break
        
        # Сохраняем в историю
        history_entry = {
            "type": "weighted",
            "input": text,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        user_history[user_id].append(history_entry)
        save_user_data(user_id)
        
        await message.answer(f"⚖️ Выбран: <b>{result}</b>", parse_mode="HTML")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}\nПроверьте формат ввода.", parse_mode="HTML")
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'show_history')
async def show_history_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    
    if user_id not in user_history or not user_history[user_id]:
        await bot.answer_callback_query(callback_query.id, "История пуста!")
        return
    
    # Получаем последние 10 записей
    recent_history = user_history[user_id][-10:]
    
    response = "📜 Последние результаты:\n\n"
    for idx, entry in enumerate(reversed(recent_history), 1):
        dt = datetime.fromisoformat(entry['timestamp']).astimezone(pytz.timezone('Europe/Moscow'))
        timestamp = dt.strftime("%d.%m.%Y %H:%M")
        
        if entry['type'] == 'number':
            response += f"{idx}. 🎲 Число: {entry['input']} → <b>{entry['result']}</b> ({timestamp})\n"
        elif entry['type'] == 'choice':
            response += f"{idx}. 🎯 Выбор: {entry['input']} → <b>{entry['result']}</b> ({timestamp})\n"
        elif entry['type'] == 'teams':
            response += f"{idx}. 👥 Команды ({timestamp})\n"
        elif entry['type'] == 'password':
            response += f"{idx}. 🔑 Пароль ({timestamp})\n"
        elif entry['type'] == 'date':
            response += f"{idx}. 📅 Дата: {entry['input']} → <b>{entry['result']}</b> ({timestamp})\n"
        elif entry['type'] == 'weighted':
            response += f"{idx}. ⚖️ Взвешенный: {entry['input']} → <b>{entry['result']}</b> ({timestamp})\n"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🧹 Очистить историю", callback_data="clear_history"))
    
    await bot.send_message(
        callback_query.from_user.id,
        response,
        parse_mode="HTML",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data == 'clear_history')
async def clear_history_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    
    if user_id in user_history:
        user_history[user_id] = []
        save_user_data(user_id)
    
    await bot.answer_callback_query(callback_query.id, "История очищена!")
    await bot.send_message(callback_query.from_user.id, "🧹 История результатов очищена.")

@dp.callback_query_handler(lambda c: c.data == 'help_info')
async def help_handler(callback_query: types.CallbackQuery):
    help_text = (
        "🆘 Помощь по RandomMaster Bot\n\n"
        "🎲 <b>Случайное число</b>\n"
        "Введите диапазон чисел (например: <code>1 100</code>)\n\n"
        "📋 <b>Случайный выбор</b>\n"
        "Введите элементы через запятую (например: <code>Яблоко, Груша, Банан</code>)\n\n"
        "👥 <b>Выбор команды</b>\n"
        "1. Введите имена участников через запятую\n"
        "2. Введите количество команд или их названия\n\n"
        "🔐 <b>Генератор пароля</b>\n"
        "Введите длину пароля (от 6 до 50 символов)\n\n"
        "🔄 <b>Перемешать список</b>\n"
        "Введите элементы через запятую\n\n"
        "📅 <b>Случайная дата</b>\n"
        "Введите диапазон дат в формате ГГГГ-ММ-ДД (например: <code>2023-01-01 2023-12-31</code>)\n\n"
        "⚖️ <b>Взвешенный выбор</b>\n"
        "Введите элементы и их веса (например: <code>Красный:3, Зеленый:2, Синий:1</code>)\n\n"
        "📜 <b>История</b>\n"
        "Показывает последние 10 результатов\n"
        "Можно очистить историю\n\n"
        "Все результаты сохраняются только для вашего удобства и нигде не публикуются."
    )
    
    await bot.send_message(
        callback_query.from_user.id,
        help_text,
        parse_mode="HTML"
    )

if __name__ == '__main__':
    # Создаем папку для данных пользователя
    os.makedirs('user_data', exist_ok=True)
    
    executor.start_polling(dp, skip_updates=True)
