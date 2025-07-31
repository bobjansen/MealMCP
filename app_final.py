from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
)
from functools import wraps
from pantry_manager_factory import create_pantry_manager
from pantry_manager_shared import SharedPantryManager
from web_auth_simple import WebUserManager
from constants import UNITS
from i18n import t
from datetime import date, timedelta, datetime
import json
import os

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY", "your-secret-key-change-this-in-production"
)

# Determine backend mode
backend = os.getenv("PANTRY_BACKEND", "sqlite")
connection_string = os.getenv("PANTRY_DATABASE_URL", "pantry.db")

# Initialize authentication manager
auth_manager = WebUserManager(backend=backend, connection_string=connection_string)

# For SQLite mode, create a single pantry manager
if backend == "sqlite":
    pantry = create_pantry_manager()
else:
    pantry = None  # Will be created per-user session


def get_current_user_pantry():
    """Get the current user's pantry manager."""
    if backend == "sqlite":
        return pantry

    if "user_id" not in session:
        return None

    user_info = auth_manager.get_user_by_id(session["user_id"])
    if not user_info:
        return None

    # Use SharedPantryManager with user_id scoping for PostgreSQL
    return SharedPantryManager(
        connection_string=connection_string,
        user_id=user_info["id"],
        backend="postgresql",
    )


def requires_auth(f):
    """Decorator to require authentication in PostgreSQL mode."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if backend == "sqlite":
            return f(*args, **kwargs)

        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


# Custom Jinja2 filters
@app.template_filter("strftime")
def strftime_filter(date_str, format="%A"):
    """Format date string."""
    try:
        if isinstance(date_str, str):
            date_obj = datetime.fromisoformat(date_str).date()
        else:
            date_obj = date_str
        return date_obj.strftime(format)
    except:
        return date_str


# Authentication routes
@app.route("/login", methods=["GET", "POST"])
def login():
    """User login page."""
    if backend == "sqlite":
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Please enter both username and password.", "error")
            return render_template("auth/login.html")

        success, user_info = auth_manager.authenticate_user(username, password)

        if success:
            session["user_id"] = user_info["id"]
            session["username"] = user_info["username"]
            flash(f'Welcome back, {user_info["username"]}!', "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "error")

    return render_template("auth/login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration page."""
    if backend == "sqlite":
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not all([username, email, password, confirm_password]):
            flash("Please fill in all fields.", "error")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html")

        success, message = auth_manager.create_user(username, email, password)

        if success:
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))
        else:
            flash(message, "error")

    return render_template("auth/register.html")


@app.route("/logout")
def logout():
    """User logout."""
    if backend == "postgresql":
        session.clear()
        flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/profile")
@requires_auth
def profile():
    """User profile page."""
    if backend == "sqlite":
        return redirect(url_for("index"))

    user_info = auth_manager.get_user_by_id(session["user_id"])
    return render_template("auth/profile.html", user=user_info)


@app.route("/change-password", methods=["POST"])
@requires_auth
def change_password():
    """Change user password."""
    if backend == "sqlite":
        return redirect(url_for("index"))

    old_password = request.form.get("old_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    if not all([old_password, new_password, confirm_password]):
        flash("Please fill in all password fields.", "error")
        return redirect(url_for("profile"))

    if new_password != confirm_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for("profile"))

    success, message = auth_manager.change_password(
        session["user_id"], old_password, new_password
    )

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("profile"))


# Main application routes
@app.route("/")
@requires_auth
def index():
    """Main dashboard page."""
    context = {"backend": backend}
    if backend == "postgresql" and "username" in session:
        context["username"] = session["username"]
    return render_template("index.html", **context)


@app.route("/preferences")
@requires_auth
def preferences():
    """Preferences management page."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    prefs = user_pantry.get_preferences()
    return render_template("preferences.html", preferences=prefs)


@app.route("/preferences/add", methods=["POST"])
@requires_auth
def add_preference():
    """Add a new preference."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data.", "error")
        return redirect(url_for("preferences"))

    category = request.form.get("category")
    item = request.form.get("item")
    level = request.form.get("level")
    notes = request.form.get("notes", "")

    if user_pantry.add_preference(category, item, level, notes):
        flash("Preference added successfully!", "success")
    else:
        flash("Error adding preference.", "error")

    return redirect(url_for("preferences"))


@app.route("/preferences/delete/<int:pref_id>", methods=["POST"])
@requires_auth
def delete_preference(pref_id):
    """Delete a preference."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data.", "error")
        return redirect(url_for("preferences"))

    if user_pantry.delete_preference(pref_id):
        flash("Preference deleted successfully!", "success")
    else:
        flash("Error deleting preference.", "error")

    return redirect(url_for("preferences"))


@app.route("/pantry")
@requires_auth
def pantry_view():
    """Pantry management page."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data.", "error")
        return redirect(url_for("logout"))

    contents = user_pantry.get_pantry_contents()
    history = user_pantry.get_transaction_history()
    return render_template(
        "pantry.html", contents=contents, history=history, units=UNITS
    )


@app.route("/pantry/add", methods=["POST"])
@requires_auth
def add_item():
    """Add item to pantry."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data.", "error")
        return redirect(url_for("pantry_view"))

    item_name = request.form.get("item_name")
    quantity = float(request.form.get("quantity", 0))
    unit = request.form.get("unit")
    notes = request.form.get("notes", "")

    if user_pantry.add_item(item_name, quantity, unit, notes):
        flash(f"Added {quantity} {unit} of {item_name} to pantry!", "success")
    else:
        flash("Error adding item to pantry.", "error")

    return redirect(url_for("pantry_view"))


@app.route("/pantry/remove", methods=["POST"])
@requires_auth
def remove_item():
    """Remove item from pantry."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data.", "error")
        return redirect(url_for("pantry_view"))

    item_name = request.form.get("item_name")
    quantity = float(request.form.get("quantity", 0))
    unit = request.form.get("unit")
    notes = request.form.get("notes", "")

    if user_pantry.remove_item(item_name, quantity, unit, notes):
        flash(f"Removed {quantity} {unit} of {item_name} from pantry!", "success")
    else:
        flash("Error removing item from pantry.", "error")

    return redirect(url_for("pantry_view"))


@app.route("/recipes")
@requires_auth
def recipes():
    """Recipes page."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data.", "error")
        return redirect(url_for("logout"))

    all_recipes = user_pantry.get_all_recipes()
    return render_template("recipes.html", recipes=all_recipes)


@app.route("/recipes/view/<recipe_name>")
@requires_auth
def view_recipe(recipe_name):
    """View a specific recipe."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data.", "error")
        return redirect(url_for("logout"))

    recipe = user_pantry.get_recipe(recipe_name)
    if not recipe:
        flash("Recipe not found.", "error")
        return redirect(url_for("recipes"))

    return render_template("recipe_view.html", recipe=recipe)


@app.route("/recipes/add", methods=["GET", "POST"])
@requires_auth
def add_recipe_form():
    """Add recipe form."""
    if request.method == "POST":
        user_pantry = get_current_user_pantry()
        if not user_pantry:
            flash("Unable to access your data.", "error")
            return redirect(url_for("recipes"))

        name = request.form.get("name")
        instructions = request.form.get("instructions")
        time_minutes = int(request.form.get("time_minutes", 0))

        # Parse ingredients
        ingredients = []
        ingredient_names = request.form.getlist("ingredient_name[]")
        ingredient_quantities = request.form.getlist("ingredient_quantity[]")
        ingredient_units = request.form.getlist("ingredient_unit[]")

        for i, name_ing in enumerate(ingredient_names):
            if name_ing.strip():
                ingredients.append(
                    {
                        "name": name_ing.strip(),
                        "quantity": float(ingredient_quantities[i]),
                        "unit": ingredient_units[i],
                    }
                )

        if user_pantry.add_recipe(name, instructions, time_minutes, ingredients):
            flash("Recipe added successfully!", "success")
            return redirect(url_for("recipes"))
        else:
            flash("Error adding recipe.", "error")

    return render_template("recipe_add.html", units=UNITS)


@app.route("/recipes/edit/<recipe_name>", methods=["GET", "POST"])
@requires_auth
def edit_recipe_form(recipe_name):
    """Edit recipe form."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data.", "error")
        return redirect(url_for("recipes"))

    recipe = user_pantry.get_recipe(recipe_name)
    if not recipe:
        flash("Recipe not found.", "error")
        return redirect(url_for("recipes"))

    if request.method == "POST":
        instructions = request.form.get("instructions")
        time_minutes = int(request.form.get("time_minutes", 0))

        # Parse ingredients
        ingredients = []
        ingredient_names = request.form.getlist("ingredient_name[]")
        ingredient_quantities = request.form.getlist("ingredient_quantity[]")
        ingredient_units = request.form.getlist("ingredient_unit[]")

        for i, name_ing in enumerate(ingredient_names):
            if name_ing.strip():
                ingredients.append(
                    {
                        "name": name_ing.strip(),
                        "quantity": float(ingredient_quantities[i]),
                        "unit": ingredient_units[i],
                    }
                )

        if user_pantry.edit_recipe(
            recipe_name, instructions, time_minutes, ingredients
        ):
            flash("Recipe updated successfully!", "success")
            return redirect(url_for("view_recipe", recipe_name=recipe_name))
        else:
            flash("Error updating recipe.", "error")

    return render_template("recipe_edit.html", recipe=recipe, units=UNITS)


@app.route("/recipes/rate/<recipe_name>", methods=["POST"])
@requires_auth
def rate_recipe(recipe_name):
    """Rate a recipe."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data.", "error")
        return redirect(url_for("recipes"))

    rating = int(request.form.get("rating", 0))

    if user_pantry.rate_recipe(recipe_name, rating):
        flash("Recipe rated successfully!", "success")
    else:
        flash("Error rating recipe.", "error")

    return redirect(url_for("view_recipe", recipe_name=recipe_name))


@app.route("/recipes/execute/<recipe_name>", methods=["POST"])
@requires_auth
def execute_recipe(recipe_name):
    """Execute a recipe (remove ingredients from pantry)."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data.", "error")
        return redirect(url_for("recipes"))

    success, message = user_pantry.execute_recipe(recipe_name)

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("view_recipe", recipe_name=recipe_name))


@app.route("/meal-plan")
@requires_auth
def meal_plan():
    """Meal planning page."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data.", "error")
        return redirect(url_for("logout"))

    # Get current week's meal plan
    today = date.today()
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=6)

    plan = user_pantry.get_meal_plan(start_date.isoformat(), end_date.isoformat())
    all_recipes = user_pantry.get_all_recipes()
    grocery_list = user_pantry.get_grocery_list()

    # Create a week structure
    week_plan = {}
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        week_plan[current_date.isoformat()] = {"date": current_date, "recipe": None}

    for meal in plan:
        if meal["date"] in week_plan:
            week_plan[meal["date"]]["recipe"] = meal["recipe"]

    return render_template(
        "meal_plan.html",
        week_plan=week_plan,
        recipes=all_recipes,
        grocery_list=grocery_list,
    )


@app.route("/meal-plan/set", methods=["POST"])
@requires_auth
def set_meal_plan():
    """Set a meal for a specific date."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data.", "error")
        return redirect(url_for("meal_plan"))

    meal_date = request.form.get("date")
    recipe_name = request.form.get("recipe")

    if user_pantry.set_meal_plan(meal_date, recipe_name):
        flash("Meal planned successfully!", "success")
    else:
        flash("Error planning meal.", "error")

    return redirect(url_for("meal_plan"))


@app.context_processor
def inject_globals():
    """Inject global variables into templates."""
    return {
        "backend": backend,
        "requires_auth": backend == "postgresql",
        "current_user": session.get("username") if backend == "postgresql" else None,
    }


if __name__ == "__main__":
    app.run(debug=True)
