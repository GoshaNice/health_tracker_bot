import asyncio
import requests
import os
from config import OPENWHEATHER_TOKEN

def get_base_calories_goal(weight: float, height: float, age: float):
    return 10 * weight + 6.25 * height - 5 * age

async def get_current_temperature(city: str, api_key: str):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = await asyncio.to_thread(requests.get, url)
    if response.ok:
        data = response.json()
        return response.ok, data["main"]["temp"]
    else:
        return response.ok, response.text

async def get_base_water_goal(weight: float, activity: float, city: str):
    base_norm = weight * 30 + 500 * activity / 30
    api_key = OPENWHEATHER_TOKEN
    status_ok, temp = await get_current_temperature(city=city, api_key=api_key)
    if not status_ok or float(temp) <= 25:
        return int(base_norm)
    else:
        return int(base_norm + 1000 + (float(temp) - 50) * 20)
    
async def get_food_calories(food_name: str):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={food_name}&json=true"
    response = await asyncio.to_thread(requests.get, url)
    if response.ok:
        data = response.json()
        products = data.get('products', [])
        if products:  # Проверяем, есть ли найденные продукты
            first_product = products[0]
            return first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
        return None
    else:
        return None


CALORIES_PER_MINUTE = {
    "бег": 10,
    "run": 10,
    "плавание": 8,
    "swimming": 8,
    "велосипед": 7,
    "bicycle": 7,
    "ходьба": 5,
    "walk": 5,
    "аэробика": 6,
    "aerobics": 6, 
    "йога": 3,
    "yoga": 3,
}

async def get_workout_spent_calories_and_water(description: str):
    workout_type, workout_minutes = description.split()
    workout_type = workout_type.lower()
    workout_minutes = int(workout_minutes)
    calories_per_min = CALORIES_PER_MINUTE.get(workout_type, 0)
    return calories_per_min * workout_minutes, (workout_minutes // 30) * 200
            
    

