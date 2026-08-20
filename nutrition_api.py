# nutrition_api.py

import json
import os
import requests
from translation_map import TRANSLATIONS


_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(_BASE_DIR, "data", "nutrition_cache.json")


DEFAULT_APP_ID = "4ab78244"
DEFAULT_APP_KEY = "2c8f940dfe2ac77498fd8b586fe9dba9"

def load_cache():
    """Loads the local nutrition cache if it exists."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Saves the current nutrition data to the local cache file."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def get_nutrition_data(item_name, app_id=None, app_key=None):
    """
    Fetches nutrition data from Edamam API, translating local dishes if necessary.
    """
    app_id = app_id or os.environ.get("EDAMAM_APP_ID", DEFAULT_APP_ID)
    app_key = app_key or os.environ.get("EDAMAM_APP_KEY", DEFAULT_APP_KEY)
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
        # If API fails
        data = {"calories": 0.0, "protein": 0.0, "allergens": []}

    # Save new data to cache
    cache[item_name] = data
    save_cache(cache)
    
    return data
