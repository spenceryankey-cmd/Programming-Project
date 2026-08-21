for item_data in cafe_data.get("menu", []):
            item_id = item_data["id"]
            name = item_data["name"]
            
            # Fix 2: Handle null prices by falling back to 0.0
            raw_price = item_data.get("price")
            price = float(raw_price) if raw_price is not None else 0.0
            
            category = item_data.get("category", "General")
            
            # Fetch nutrition data (hits local cache automatically)
            nutrition = get_nutrition_data(name)
            
            # Fix 3: Remove "category" from kwargs to avoid the duplicate argument error
            kwargs = {
                "item_id": item_id,
                "name": name,
                "price": price,
                "calories": nutrition["calories"],
                "protein": nutrition["protein"],
                "allergens": nutrition["allergens"]
            }

            # Instantiate polymorphic subclasses based on category
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
