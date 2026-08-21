# nutrition_api.py

import json
import os
import requests
from translation_map import TRANSLATIONS

CACHE_FILE = "data/nutrition_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def get_nutrition_data(item_name, app_id=None, app_key=None):
    """
    Fetches nutrition data from Edamam API using environment variables or fallbacks.
    """
    app_id = app_id or os.getenv("EDAMAM_APP_ID", "4ab78244")
    app_key = app_key or os.getenv("EDAMAM_APP_KEY", "2c8f940dfe2ac77498fd8b586fe9dba9")
    
    cache = load_cache()
    if item_name in cache:
        return cache[item_name]
        
    query = TRANSLATIONS.get(item_name, item_name)
    url = "https://api.edamam.com/api/food-database/v2/parser"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "ingr": query
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data_json = response.json()
        
        parsed_food = data_json["parsed"][0]["food"]
        nutrients = parsed_food.get("nutrients", {})
        
        data = {
            "calories": round(nutrients.get("ENERC_KCAL", 0), 1),
            "protein": round(nutrients.get("PROCNT", 0), 1),
            "allergens": parsed_food.get("healthLabels", [])
        }
    except (IndexError, KeyError, requests.RequestException):
        data = {"calories": 0.0, "protein": 0.0, "allergens": []}

    cache[item_name] = data
    save_cache(cache)
    return data
