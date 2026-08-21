# nutrition_api.py
import json
import os
import requests
from translation_map import TRANSLATIONS

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(_BASE_DIR, "data", "nutrition_cache.json")

# TheMealDB's shared test key. This one is public/free by design (not a
# secret like the Edamam keys were) - a paid key later should still come
# from an environment variable rather than being hardcoded here.
DEFAULT_API_KEY = "1"
BASE_URL = "https://www.themealdb.com/api/json/v1"


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


def get_nutrition_data(item_name, api_key=None):
    """
    Fetches ingredient data for item_name from TheMealDB, translating
    local dish names to a searchable term first if needed.

    TheMealDB has no nutrition or allergen fields - it only returns a
    matched recipe's ingredient/measure list. Treat this as a first-pass
    ingredient reference to build allergen tags from yourself, same as
    the standard-recipe caveat already in README_allergens.md.
    """
    api_key = api_key or os.environ.get("MEALDB_API_KEY", DEFAULT_API_KEY)

    cache = load_cache()
    if item_name in cache:
        return cache[item_name]

    query = TRANSLATIONS.get(item_name, item_name)

    url = f"{BASE_URL}/{api_key}/search.php"
    params = {"s": query}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data_json = response.json()

        meals = data_json.get("meals")
        if not meals:
            raise IndexError("No meals found for query")

        meal = meals[0]

        ingredients = []
        for i in range(1, 21):
            ingr = meal.get(f"strIngredient{i}")
            measure = meal.get(f"strMeasure{i}")
            if ingr and ingr.strip():
                ingredients.append({
                    "ingredient": ingr.strip(),
                    "measure": (measure or "").strip()
                })

        data = {
            "source": "TheMealDB",
            "matched_name": meal.get("strMeal", query),
            "category": meal.get("strCategory", ""),
            "area": meal.get("strArea", ""),
            "ingredients": ingredients
        }
    except (IndexError, KeyError, requests.RequestException):
        data = {
            "source": "TheMealDB",
            "matched_name": None,
            "category": "",
            "area": "",
            "ingredients": []
        }

    cache[item_name] = data
    save_cache(cache)

    return data
