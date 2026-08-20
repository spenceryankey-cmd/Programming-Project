# cafeterias.py

import json
import os
from models import Cafeteria, Entree, Beverage, Snack
from nutrition_api import get_nutrition_data

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_JSON_PATH = os.path.join(_BASE_DIR, "data", "cafeteria_menus.json")

def load_all_cafeterias(json_path=_DEFAULT_JSON_PATH):
    """
    Loads all cafeterias and their menu items from the JSON file
    """
    if not os.path.exists(json_path):
        return {}

    with open(json_path, "r") as f:
        data = json.load(f)

    cafeterias_dict = {}

    for cafe_data in data.get("cafeterias", []):
        cafe_id = cafe_data["id"]
        cafe_name = cafe_data["name"]
        schedule = cafe_data.get("schedule", {})
        
        cafe = Cafeteria(cafe_id, cafe_name, schedule)

        for item_data in cafe_data.get("menu", []):
            item_id = item_data["id"]
            name = item_data["name"]
            price = item_data["price"]
            category = item_data.get("category", "General")
            
            nutrition = get_nutrition_data(name)
            
            kwargs = {
                "item_id": item_id,
                "name": name,
                "price": price,
                "calories": nutrition["calories"],
                "protein": nutrition["protein"],
                "allergens": nutrition["allergens"]
            }

            if category == "Entree":
                meal_period = item_data.get("meal_period", "Lunch")
                item = Entree(meal_period=meal_period, **kwargs)
            elif category == "Beverage":
                is_cold = item_data.get("is_cold", True)
                item = Beverage(is_cold=is_cold, **kwargs)
            elif category == "Snack":
                restricted_days = item_data.get("restricted_days", [])
                item = Snack(restricted_days=restricted_days, **kwargs)
            else:
                item = Entree(**kwargs)

            cafe.add_item(item)

        cafeterias_dict[cafe_name] = cafe

    return cafeterias_dict


ALL_CAFES = load_all_cafeterias()

def get_menu(cafeteria_name, date="Monday"):
    """Returns all menu items for a specific cafeteria."""
    cafe = ALL_CAFES.get(cafeteria_name)
    if cafe:
        return [item.to_dict() for item in cafe.menu_items]
    return []

def get_items_available_at(current_time="12:00", current_day="Monday"):
    """Returns all items currently available across all cafeterias based on time and day."""
    available_results = []
    for cafe_name, cafe in ALL_CAFES.items():
        items = cafe.get_available_items(current_time, current_day)
        for item in items:
            item_dict = item.to_dict()
            item_dict["cafeteria"] = cafe_name
            available_results.append(item_dict)
    return available_results

def search_by_name(query_str):
    """Performs a case-insensitive string search across all menu items."""
    query_str = query_str.lower()
    matches = []
    for cafe_name, cafe in ALL_CAFES.items():
        for item in cafe.menu_items:
            if query_str in item.name.lower():
                item_dict = item.to_dict()
                item_dict["cafeteria"] = cafe_name
                matches.append(item_dict)
    return matches
