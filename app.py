import secrets
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, session, redirect, url_for

from cafeterias import ALL_CAFES, get_menu, get_items_available_at, search_by_name
from planner import (
    recommend_meal_plan,
    BudgetLimit,
    AllergenFilter,
    CalorieGoal,
    ProteinGoal,
    CafeteriaVariety,
)
from users import create_user, verify_user

app = Flask(__name__)

app.secret_key = secrets.token_hex(32)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def index():
    #Home page: list all cafeterias.
    cafeterias = [
        {"name": name, "item_count": len(cafe.menu_items)}
        for name, cafe in ALL_CAFES.items()
    ]
    return render_template("index.html", cafeterias=cafeterias)


@app.route("/cafeteria/<cafeteria_name>")
def cafeteria_menu(cafeteria_name):
    #Full menu for a single cafeteria.
    items = get_menu(cafeteria_name)
    return render_template(
        "cafeteria_menu.html", cafeteria_name=cafeteria_name, items=items
    )


@app.route("/available", methods=["GET"])
def available_now():
    #Items available at a given time (automatically at right now).
    now = datetime.now()
    default_time = now.strftime("%H:%M")
    default_day = DAYS[now.weekday()]

    current_time = request.args.get("time", default_time)
    current_day = request.args.get("day", default_day)

    items = get_items_available_at(current_time=current_time, current_day=current_day)

    return render_template(
        "available.html",
        items=items,
        current_time=current_time,
        current_day=current_day,
        days=DAYS,
    )


@app.route("/search", methods=["GET"])
def search():
    """Search menu items by name across all cafeterias."""
    query = request.args.get("q", "").strip()
    results = search_by_name(query) if query else []
    return render_template("search.html", query=query, results=results)


@app.route("/planner", methods=["GET"])
@login_required
def planner_page():
    """Build a full-day meal plan from user-supplied dietary constraints."""
    day = request.args.get("day", DAYS[0])
    budget = request.args.get("budget", "").strip()
    exclude = request.args.get("exclude", "").strip()
    cal_min = request.args.get("cal_min", "").strip()
    cal_max = request.args.get("cal_max", "").strip()
    protein_min = request.args.get("protein_min", "").strip()
    max_per_cafe = request.args.get("max_per_cafe", "2").strip()

    submitted = bool(request.args)
    plan = []
    totals = None
    error = None

    if submitted:
        try:
            constraints = []

            if budget:
                constraints.append(BudgetLimit(max_total=float(budget)))

            excluded_labels = [x.strip() for x in exclude.split(",") if x.strip()]
            if excluded_labels:
                constraints.append(AllergenFilter(excluded_labels=excluded_labels))

            if cal_min or cal_max:
                lo = float(cal_min) if cal_min else 0
                hi = float(cal_max) if cal_max else 100000
                constraints.append(CalorieGoal(min_calories=lo, max_calories=hi))

            if protein_min:
                constraints.append(ProteinGoal(min_protein=float(protein_min)))

            constraints.append(
                CafeteriaVariety(max_visits_per_cafeteria=int(max_per_cafe or 2))
            )

            plan = recommend_meal_plan(constraints, day=day)

            if plan:
                totals = {
                    "price": sum(item.get("price", 0) or 0 for _, item, _ in plan),
                    "calories": sum(item.get("calories", 0) or 0 for _, item, _ in plan),
                    "protein": sum(item.get("protein", 0) or 0 for _, item, _ in plan),
                }
        except ValueError:
            error = "Budget, calorie, and protein fields must be numbers."

    return render_template(
        "planner.html",
        days=DAYS,
        day=day,
        budget=budget,
        exclude=exclude,
        cal_min=cal_min,
        cal_max=cal_max,
        protein_min=protein_min,
        max_per_cafe=max_per_cafe,
        submitted=submitted,
        plan=plan,
        totals=totals,
        error=error,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    #For creating a new account
    error = None
    username = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if password != confirm:
            error = "Passwords don't match."
        else:
            ok, message = create_user(username, password)
            if ok:
                session["username"] = username
                return redirect(url_for("index"))
            error = message

    return render_template("register.html", error=error, username=username)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log in to an existing account."""
    error = None
    username = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if verify_user(username, password):
            session["username"] = username
            next_url = request.args.get("next") or url_for("index")
            return redirect(next_url)
        error = "Incorrect username or password."

    return render_template("login.html", error=error, username=username)


@app.route("/logout")
def logout():
    """Log out the current user."""
    session.pop("username", None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
