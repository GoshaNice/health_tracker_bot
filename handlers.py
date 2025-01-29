from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import Form
import aiohttp
from utils import get_base_calories_goal, get_base_water_goal, get_food_calories, get_workout_spent_calories_and_water

router = Router()
users_data = {}

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("Добро пожаловать! Я ваш бот.\nВведите /help для списка команд.")

# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/set_profile - Настройка профиля\n"
        "/log_water <кол-во в мл> - Логгирование потребленной воды\n"
        "/log_food <продукт> - Логгирование потребленной пищи\n"
        "/log_workout <тип тренировки> <длительность в минутах> - Логгирование тренировки\n"
        "/check_progress - Текущий прогресс"
    )

# FSM: диалог с пользователем
@router.message(Command("set_profile"))
async def start_form(message: Message, state: FSMContext):
    await message.answer("Введите ваш вес (в кг)")
    await state.set_state(Form.weight)

@router.message(Form.weight)
async def process_weight(message: Message, state: FSMContext):
    await state.update_data(weight=float(message.text))
    await message.answer("Введите ваш рост (в см)")
    await state.set_state(Form.height)
    
@router.message(Form.height)
async def process_height(message: Message, state: FSMContext):
    await state.update_data(height=float(message.text))
    await message.answer("Введите ваш возраст")
    await state.set_state(Form.age)

@router.message(Form.age)
async def process_age(message: Message, state: FSMContext):
    await state.update_data(age=float(message.text))
    await message.answer("Сколько минут активности у вас в день?")
    await state.set_state(Form.activity)

@router.message(Form.activity)
async def process_activity(message: Message, state: FSMContext):
    await state.update_data(activity=float(message.text))
    await message.answer("В каком городе вы находитесь?")
    await state.set_state(Form.city)

@router.message(Form.city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    data = await state.get_data()
    base_calories_goal = get_base_calories_goal(weight = data.get("weight"), 
                                                height = data.get("height"),
                                                age = data.get("age"))
    await state.update_data(calorie_goal=base_calories_goal)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="change")],
            [InlineKeyboardButton(text="Нет", callback_data="save")],
        ]
    )
    await message.answer(f"Ваша базовая цель по калориям составляет {base_calories_goal}. Хотите поменять?", reply_markup=keyboard)
    await state.set_state(Form.calorie_goal)

@router.callback_query(Form.calorie_goal)
async def process_calories_decision(callback_query, state: FSMContext):
    if callback_query.data == "change":
        await callback_query.message.answer("Введите желаемую цель по каллориям")
        await state.set_state(Form.calorie_choose)
    elif callback_query.data == "save":
        data = await state.get_data()
        users_data[callback_query.from_user.username] = data
        await callback_query.message.answer("Ваши данные сохранены")
        await state.clear()

@router.message(Form.calorie_choose)
async def process_activity(message: Message, state: FSMContext):
    await state.update_data(calorie_goal=float(message.text))
    data = await state.get_data()
    users_data[message.from_user.username] = data
    await message.answer("Ваши данные сохранены")
    await state.clear()

# --------------------------------

@router.message(Command("log_water"))
async def log_water(message: Message):
    username = message.from_user.username
    data = users_data.get(username, {})
    base_water_norm = await get_base_water_goal(weight=data.get("weight", 0), activity=data.get("activity", 0), city=data.get("city", 0))
    logged_water = data.get("logged_water", 0)
    logged_water += float(message.text.split()[1])
    users_data[username]["logged_water"] = logged_water
    remaining_water = max(0, base_water_norm - logged_water)
    if remaining_water > 0:
        message_remaining = f"Сегодня нужно выпить еще {remaining_water} мл."
    else:
        message_remaining = f"Вы выполнили норму, отлично!"
    await message.answer(f"За сегодня вы выпили {logged_water} из {base_water_norm} мл воды. {message_remaining}")


@router.message(Command("log_food"))
async def log_food(message: Message, state: FSMContext):
    username = message.from_user.username
    data = users_data.get(username, {})
    
    food_name = message.text.removeprefix("/log_food").strip()
    # users_data[username]["last_food_consumed"] = food_name
    calories_per_100g = await get_food_calories(food_name = food_name)
    users_data[username]["last_food_calories"] = calories_per_100g
    await message.answer(f"{food_name} — {calories_per_100g} ккал на 100 г. Сколько грамм вы съели?")
    await state.set_state(Form.food_consumed)


@router.message(Form.food_consumed)
async def process_food_consumed(message: Message, state: FSMContext):
    username = message.from_user.username
    food_consumed = float(message.text)
    data = users_data.get(username, {})
    last_food_calories = data.get("last_food_calories", 0)
    
    calories_consumed = last_food_calories * food_consumed / 100
    await message.answer(f"Записано: {calories_consumed} ккал.")

    last_logged_calories = users_data[username].get("logged_calories", 0)
    users_data[username]["logged_calories"] = last_logged_calories + calories_consumed
    await state.clear()


@router.message(Command("log_workout"))
async def log_workout(message: Message):
    username = message.from_user.username
    data = users_data.get(username, {})
    
    workout_description = message.text.removeprefix("/log_workout").strip()
    calories_spent, water_spent = await get_workout_spent_calories_and_water(description=workout_description)

    burned_calories = data.get("burned_calories", 0)
    burned_calories += calories_spent
    users_data[username]["burned_calories"] = burned_calories
    
    message_water = ""
    if water_spent > 0:
        message_water = f" Дополнительно выпейте {water_spent} мл воды."
    await message.answer(f"{workout_description} минут - записано {calories_spent} ккал.{message_water}")

# --------------------------------

@router.message(Command("check_progress"))
async def check_progress(message: Message, state: FSMContext):
    username = message.from_user.username
    data = users_data.get(username, {})
    logged_water = data.get("logged_water", 0)
    base_water_norm = await get_base_water_goal(weight=data.get("weight", 0), activity=data.get("activity", 0), city=data.get("city", 0))
    water_left_to_goal = max(0, base_water_norm - logged_water)
    
    logged_calories = data.get("logged_calories", 0)
    burned_calories = data.get("burned_calories", 0)
    calorie_goal = data.get("calorie_goal", 0)
    calorie_balance = calorie_goal + burned_calories - logged_calories

    await message.reply(f"📊 Прогресс:\nВода:\n- Выпито: {logged_water} мл из {base_water_norm} мл.\n- Осталось: {water_left_to_goal} мл.\n\nКалории:\n- Потреблено: {logged_calories} ккал из {calorie_goal} ккал.\n- Сожжено: {burned_calories} ккал.\n- Баланс: {calorie_balance} ккал.")

# --------------------------------

# Функция для подключения обработчиков
def setup_handlers(dp):
    dp.include_router(router)
