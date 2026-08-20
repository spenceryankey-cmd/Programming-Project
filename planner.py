
#BAckend for planner
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash

from cafeterias import get_items_available_at

def default_slots():
    #Returns the standard set of slots a full day's plan is built from.
    return [
        {"name": "breakfast", "time": "08:00", "mandatory": True},
        {"name": "lunch", "time": "12:30", "mandatory": True},
        {"name": "dinner", "time": "18:30", "mandatory": True},
        {"name": "snack", "time": "15:00", "mandatory": False},
        {"name": "beverage", "time": "12:30", "mandatory": False},
    ]


def categories_for_slot(slot_name):
    #Maps a meal slot to the menu-item categories that can fill it.
    match slot_name:
        case "breakfast" | "lunch" | "dinner":
            return ("Entree",)
        case "snack":
            return ("Snack",)
        case "beverage":
            return ("Beverage",)
        case _:
            return ()


@dataclass(frozen=True)
class PlanEntry:
    #One chosen item within a plan: where it's from, what it is, and when.
    cafeteria: str
    item: dict
    time_slot: str
    clock_time: str

def _total_price(plan):
    return sum(entry.item.get("price", 0) or 0 for entry in plan)

def _total_calories(plan):
    return sum(entry.item.get("calories", 0) or 0 for entry in plan)

def _total_protein(plan):
    return sum(entry.item.get("protein", 0) or 0 for entry in plan)

class DietaryConstraint(ABC):
    @abstractmethod
    def is_satisfied(self, plan):
        raise NotImplementedError

    def prune_check(self, partial_plan):
        return True

    def describe(self):
        return self.__class__.__name__


class BudgetLimit(DietaryConstraint):
    #Total plan cost must not exceed max_total.

    def __init__(self, max_total):
        self.max_total = max_total

    def is_satisfied(self, plan):
        return _total_price(plan) <= self.max_total

    def prune_check(self, partial_plan):
        return _total_price(partial_plan) <= self.max_total

    def describe(self):
        return f"Budget <= GHS {self.max_total:.2f}"


class AllergenFilter(DietaryConstraint):
    #No item in the plan may carry one of the excluded allergen/health labels.

    def __init__(self, excluded_labels):
        self.excluded_labels = {label.upper() for label in excluded_labels}

    def is_satisfied(self, plan):
        return all(self._item_is_safe(entry.item) for entry in plan)

    def prune_check(self, partial_plan):
        if not partial_plan:
            return True
        # Only need to check the item that was just added.
        return self._item_is_safe(partial_plan[-1].item)

    def _item_is_safe(self, item):
        item_labels = {label.upper() for label in item.get("allergens", [])}
        return self.excluded_labels.isdisjoint(item_labels)

    def describe(self):
        labels = ", ".join(sorted(self.excluded_labels)) if self.excluded_labels else "nothing"
        return f"Avoid: {labels}"


class CalorieGoal(DietaryConstraint):
    #Total plan calories must land within [min_calories, max_calories].

    def __init__(self, min_calories, max_calories):
        self.min_calories = min_calories
        self.max_calories = max_calories

    def is_satisfied(self, plan):
        total = _total_calories(plan)
        return self.min_calories <= total <= self.max_calories

    def prune_check(self, partial_plan):
        return _total_calories(partial_plan) <= self.max_calories

    def describe(self):
        return f"{self.min_calories}-{self.max_calories} kcal/day"


class ProteinGoal(DietaryConstraint):
    #Total plan protein must meet or exceed min_protein (grams).

    def __init__(self, min_protein):
        self.min_protein = min_protein

    def is_satisfied(self, plan):
        return _total_protein(plan) >= self.min_protein


    def describe(self):
        return f"At least {self.min_protein}g protein/day"


class CafeteriaVariety(DietaryConstraint):
    #Caps how many items in the plan can come from the same cafeteria.

    def __init__(self, max_visits_per_cafeteria=2):
        self.max_visits = max_visits_per_cafeteria

    def is_satisfied(self, plan):
        return self._within_limits(plan)

    def prune_check(self, partial_plan):
        return self._within_limits(partial_plan)

    def _within_limits(self, plan):
        counts = {}
        for entry in plan:
            counts[entry.cafeteria] = counts.get(entry.cafeteria, 0) + 1
            if counts[entry.cafeteria] > self.max_visits:
                return False
        return True

    def describe(self):
        return f"Max {self.max_visits} item(s) per cafeteria"


def gather_candidates(day, slot): 
    accepted_categories = categories_for_slot(slot["name"])
    if not accepted_categories:
        return []

    raw_items = get_items_available_at(current_time=slot["time"], current_day=day)

    candidates = [
        PlanEntry(
            cafeteria=item["cafeteria"],
            item=item,
            time_slot=slot["name"],
            clock_time=slot["time"],
        )
        for item in raw_items
        if item.get("category") in accepted_categories
    ]
    return candidates


def _candidate_heuristic(entry):
    item = entry.item
    protein = item.get("protein", 0) or 0
    price = item.get("price", 0) or 0
    return protein - (price * 0.1) if price else protein

def score_plan(plan, constraints=None):
    if not plan:
        return float("-inf")

    total_protein = _total_protein(plan)
    total_price = _total_price(plan)
    total_calories = _total_calories(plan)

    score = (total_protein * 2.0) - (total_price * 0.5)

    if constraints:
        for constraint in constraints:
            if isinstance(constraint, CalorieGoal):
                midpoint = (constraint.min_calories + constraint.max_calories) / 2
                distance = abs(total_calories - midpoint)
                # Ternary feasibility-adjacent bonus/penalty
                score += 50 if distance < 100 else -distance * 0.1

    return score

def try_slot(slot_index, slots, partial_plan, constraints, day, tracker, max_branch=6):
    if slot_index == len(slots):
        if all(constraint.is_satisfied(partial_plan) for constraint in constraints):
            score = score_plan(partial_plan, constraints)
            if tracker["best_plan"] is None or score > tracker["best_score"]:
                tracker["best_plan"] = list(partial_plan)
                tracker["best_score"] = score
        return

    slot = slots[slot_index]
    candidates = gather_candidates(day, slot)
    candidates.sort(key=_candidate_heuristic, reverse=True)
    candidates = candidates[:max_branch]

    tryable = candidates if slot["mandatory"] else candidates + [None]

    for candidate in tryable:
        if candidate is not None:
            partial_plan.append(candidate)

        feasible = all(constraint.prune_check(partial_plan) for constraint in constraints)
        branch_action = "descend" if feasible else "prune"

        if branch_action == "descend":
            try_slot(slot_index + 1, slots, partial_plan, constraints, day, tracker, max_branch)

        if candidate is not None:
            partial_plan.pop()  


class User:
    def __init__(self, name, password, constraints=None):
        self.name = name
        self.password_hash = generate_password_hash(password)
        self.constraints = constraints if constraints is not None else []

    def check_password(self, attempt):
        return check_password_hash(self.password_hash, attempt)

    def add_constraint(self, constraint):
        self.constraints.append(constraint)

    def __repr__(self):
        return f"User(name={self.name!r})"


@dataclass
class UserProfile:
    name: str
    constraints: list


def _extract_constraints(user):
    if hasattr(user, "constraints"):
        return list(user.constraints)
    if isinstance(user, (list, tuple)):
        return list(user)
    raise TypeError(
        "user must have constraints"
    )


def recommend_meal_plan(user, day="Monday", max_branch=6):
    constraints = _extract_constraints(user)
    slots = default_slots()

    tracker = {"best_plan": None, "best_score": float("-inf")}
    try_slot(0, slots, [], constraints, day, tracker, max_branch)

    if tracker["best_plan"] is None:
        return []

    return [(entry.cafeteria, entry.item, entry.time_slot) for entry in tracker["best_plan"]]


if __name__ == "__main__":
    demo_user = User(
        name="Ama",
        password="hunter2",
        constraints=[
            BudgetLimit(max_total=80),
            AllergenFilter(excluded_labels=["TREE_NUT_FREE"]),
            CalorieGoal(min_calories=800, max_calories=2200),
            ProteinGoal(min_protein=20),
            CafeteriaVariety(max_visits_per_cafeteria=2),
        ],
    )

    plan = recommend_meal_plan(demo_user, day="Monday")
    if not plan:
        print("No plan satisfies the given constraints.")
    else:
        for cafeteria, item, time_slot in plan:
            print(f"{time_slot:9s} | {cafeteria:15s} | {item['name']:30s} | GHS {item['price']}")
