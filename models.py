# models.py

class MenuItem:
    """Base class representing a generic cafeteria menu item."""
    def __init__(self, item_id, name, price, category="General", calories=0.0, protein=0.0, allergens=None):
        self.item_id = item_id
        self.name = name
        self.price = float(price)
        self.category = category
        self.calories = calories
        self.protein = protein
        self.allergens = allergens if allergens is not None else []

    def is_available_now(self, current_time="12:00", current_day="Monday"):
        """Default availability check; can be overridden by subclasses."""
        return True

    def to_dict(self):

        return {
            "id": self.item_id,
            "name": self.name,
            "price": self.price,
            "category": self.category,
            "calories": self.calories,
            "protein": self.protein,
            "allergens": self.allergens
        }


class Entree(MenuItem):
    """Subclass for main meals with meal-period restrictions (e.g., Breakfast vs. Lunch)."""
    def __init__(self, item_id, name, price, meal_period="Lunch", **kwargs):
        super().__init__(item_id, name, price, category="Entree", **kwargs)
        self.meal_period = meal_period

    def is_available_now(self, current_time="12:00", current_day="Monday"):
        hour = int(current_time.split(":")[0])
        # Breakfast ends at 11:00 AM
        if self.meal_period == "Breakfast" and hour >= 11:
            return False
        return True


class Beverage(MenuItem):
    """Subclass for drinks."""
    def __init__(self, item_id, name, price, is_cold=True, **kwargs):
        super().__init__(item_id, name, price, category="Beverage", **kwargs)
        self.is_cold = is_cold


class Snack(MenuItem):
    """Subclass for snacks with specific day restrictions (e.g., Kelewele days)."""
    def __init__(self, item_id, name, price, restricted_days=None, **kwargs):
        super().__init__(item_id, name, price, category="Snack", **kwargs)
        self.restricted_days = restricted_days if restricted_days else []

    def is_available_now(self, current_time="12:00", current_day="Monday"):
        if current_day in self.restricted_days:
            return False
        return True


class Cafeteria:
    """Encapsulates a cafeteria location, operating schedule, and item list."""
    def __init__(self, cafeteria_id, name, schedule=None):
        self.cafeteria_id = cafeteria_id
        self.name = name
        self.schedule = schedule if schedule else {}
        self.menu_items = []

    def add_item(self, item: MenuItem):
        self.menu_items.append(item)

    def get_available_items(self, current_time="12:00", current_day="Monday"):
        """Returns all items currently available based on time and day criteria."""
        return [
            item for item in self.menu_items 
            if item.is_available_now(current_time, current_day)
        ]
