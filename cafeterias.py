# cafeterias.py

import json
import os
from models import Cafeteria, Entree, Beverage, Snack
from nutrition_api import get_nutrition_data

def load_all_cafeterias(json_path="data/cafeteria_menus.json"):
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
            price = item_data.get("price") or 0.0
            category = item_data.get("category", "General")
            
            nutrition = get_nutrition_data(name)
            
            kwargs = {
                "item_id": item_id,
                "name": name,
                "price": float(price),
                "calories": nutrition["calories"],
                "protein": nutrition["protein"],
                "allergens": nutrition["allergens"]
            }

            # Instantiate polymorphic subclasses based on category
            if category.lower() in ["breakfast", "entree", "lunch_dinner", "food"]:
                item = Entree(**kwargs)
            elif category.lower() == "beverage":
                item = Beverage(**kwargs)
            elif category.lower() == "snack":
                item = Snack(**kwargs)
            else:
                item = Entree(**kwargs)

            cafe.add_item(item)

        cafeterias_dict[cafe_name] = cafe

    return cafeterias_dict

ALL_CAFES = load_all_cafeterias()

def get_menu(cafeteria_name):
    cafe = ALL_CAFES.get(cafeteria_name)
    if cafe:
        return [item.to_dict() for item in cafe.menu_items]
    return []

def get_items_available_at(current_time="12:00", current_day="Monday"):
    available_results = []
    for cafe_name, cafe in ALL_CAFES.items():
        items = cafe.get_available_items(current_time, current_day)
        for item in items:
            item_dict = item.to_dict()
            item_dict["cafeteria"] = cafe_name
            available_results.append(item_dict)
    return available_results

def search_by_name(query_str):
    query_str = query_str.lower()
    matches = []
    for cafe_name, cafe in ALL_CAFES.items():
        for item in cafe.menu_items:
            if query_str in item.name.lower():
                item_dict = item.to_dict()
                item_dict["cafeteria"] = cafe_name
                matches.append(item_dict)
    return matches
