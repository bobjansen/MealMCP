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
from i18n import t, set_lang
from datetime import date, timedelta, datetime
import json
import os
import secrets

# Generate secret key if not provided
secret_key = os.getenv("FLASK_SECRET_KEY")
if not secret_key:
    secret_key = secrets.token_urlsafe(32)
    os.environ["FLASK_SECRET_KEY"] = secret_key
    print(f"Generated Flask secret key: {secret_key}")


app = Flask(__name__)
app.secret_key = secret_key

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
        # For SQLite mode, check for session language preference
        session_lang = session.get("language", "en")
        set_lang(session_lang)
        return pantry

    if "user_id" not in session:
        return None

    user_info = auth_manager.get_user_by_id(session["user_id"])
    if not user_info:
        return None

    # Set language based on user preference
    set_lang(user_info.get("preferred_language", "en"))

    # Use SharedPantryManager with user_id scoping for PostgreSQL
    return SharedPantryManager(
        connection_string=connection_string,
        user_id=user_info["id"],
        backend="postgresql",
    )


@app.before_request
def set_language():
    """Set language before each request."""
    if backend == "sqlite":
        # For SQLite mode, use session language
        session_lang = session.get("language", "en")
        set_lang(session_lang)
    elif "user_id" in session:
        # For PostgreSQL mode, use user's preferred language
        user_info = auth_manager.get_user_by_id(session["user_id"])
        if user_info:
            set_lang(user_info.get("preferred_language", "en"))
        else:
            set_lang("en")
    else:
        set_lang("en")


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
        language = request.form.get("language", "en")

        if not all([username, email, password, confirm_password]):
            flash("Please fill in all fields.", "error")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html")

        if language not in ["en", "nl"]:
            language = "en"  # Default to English if invalid language

        success, message = auth_manager.create_user(username, email, password, language)

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


@app.route("/change-language", methods=["POST"])
@requires_auth
def change_language():
    """Change user's preferred language."""
    if backend == "sqlite":
        # In SQLite mode, just set the session language
        language = request.form.get("language", "en")
        if language in ["en", "nl"]:
            session["language"] = language
            set_lang(language)
            flash("Language preference updated!", "success")
        else:
            flash("Unsupported language.", "error")
        return redirect(url_for("profile"))

    language = request.form.get("language")
    if not language:
        flash("Please select a language.", "error")
        return redirect(url_for("profile"))

    success, message = auth_manager.set_user_language(session["user_id"], language)

    if success:
        set_lang(language)  # Update current session language immediately
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("profile"))


@app.route("/")
def index():
    """Main dashboard or landing page."""
    if backend == "sqlite":
        # For SQLite mode, go directly to dashboard
        context = {"backend": backend}
        return render_template("index.html", **context)

    if "user_id" in session:
        # User is logged in, show dashboard
        context = {"backend": backend}
        if "username" in session:
            context["username"] = session["username"]
        return render_template("index.html", **context)
    else:
        # User is not logged in, show landing page
        return render_template("landing.html")


@app.route("/dashboard")
@requires_auth
def dashboard():
    """Main dashboard page (protected)."""
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

    # Get current user info for household size
    current_user_info = None
    if backend == "postgresql" and "user_id" in session:
        current_user_info = auth_manager.get_user_by_id(session["user_id"])

    return render_template(
        "preferences.html", preferences=prefs, current_user_info=current_user_info
    )


@app.route("/preferences/add", methods=["POST"])
@requires_auth
def add_preference():
    """Add a new preference."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    category = request.form.get("category")
    item = request.form.get("item")
    level = request.form.get("level")
    notes = request.form.get("notes", "")

    if user_pantry.add_preference(category, item, level, notes):
        flash("Preference added successfully!", "success")
    else:
        flash("Error adding preference.", "error")

    return redirect(url_for("preferences"))


@app.route("/preferences/delete/<int:pref_id>")
@requires_auth
def delete_preference(pref_id):
    """Delete a preference."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

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
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    contents = user_pantry.get_pantry_contents()
    transactions = user_pantry.get_transaction_history()
    return render_template(
        "pantry.html", contents=contents, transactions=transactions, units=UNITS
    )


@app.route("/pantry/add", methods=["POST"])
@requires_auth
def add_pantry_item():
    """Add item to pantry."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

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
def remove_pantry_item():
    """Remove item from pantry."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

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
    """Recipe management page."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    recipes_list = user_pantry.get_all_recipes()
    return render_template("recipes.html", recipes=recipes_list)


@app.route("/recipes/view/<recipe_name>")
@requires_auth
def view_recipe(recipe_name):
    """View a specific recipe."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    recipe = user_pantry.get_recipe(recipe_name)
    if not recipe:
        flash("Recipe not found.", "error")
        return redirect(url_for("recipes"))
    return render_template("recipe_view.html", recipe=recipe)


@app.route("/recipes/add")
@requires_auth
def add_recipe_form():
    """Show add recipe form."""
    return render_template("recipe_add.html", units=UNITS)


@app.route("/recipes/add", methods=["POST"])
@requires_auth
def add_recipe():
    """Add a new recipe."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    name = request.form.get("name")
    instructions = request.form.get("instructions")
    time_minutes = int(request.form.get("time_minutes", 0))

    # Parse ingredients from form
    ingredients = []
    ingredient_names = request.form.getlist("ingredient_name[]")
    ingredient_quantities = request.form.getlist("ingredient_quantity[]")
    ingredient_units = request.form.getlist("ingredient_unit[]")

    for i in range(len(ingredient_names)):
        if ingredient_names[i]:  # Skip empty ingredient names
            ingredients.append(
                {
                    "name": ingredient_names[i],
                    "quantity": float(ingredient_quantities[i]),
                    "unit": ingredient_units[i],
                }
            )

    if user_pantry.add_recipe(name, instructions, time_minutes, ingredients):
        flash(f'Recipe "{name}" added successfully!', "success")
        return redirect(url_for("recipes"))
    else:
        flash("Error adding recipe.", "error")
        return redirect(url_for("add_recipe_form"))


@app.route("/recipes/edit/<recipe_name>")
@requires_auth
def edit_recipe_form(recipe_name):
    """Show edit recipe form."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    recipe = user_pantry.get_recipe(recipe_name)
    if not recipe:
        flash("Recipe not found.", "error")
        return redirect(url_for("recipes"))
    return render_template("recipe_edit.html", recipe=recipe, units=UNITS)


@app.route("/recipes/edit/<recipe_name>", methods=["POST"])
@requires_auth
def edit_recipe(recipe_name):
    """Edit an existing recipe."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    instructions = request.form.get("instructions")
    time_minutes = int(request.form.get("time_minutes", 0))

    # Parse ingredients from form
    ingredients = []
    ingredient_names = request.form.getlist("ingredient_name[]")
    ingredient_quantities = request.form.getlist("ingredient_quantity[]")
    ingredient_units = request.form.getlist("ingredient_unit[]")

    for i in range(len(ingredient_names)):
        if ingredient_names[i]:  # Skip empty ingredient names
            ingredients.append(
                {
                    "name": ingredient_names[i],
                    "quantity": float(ingredient_quantities[i]),
                    "unit": ingredient_units[i],
                }
            )

    if user_pantry.edit_recipe(recipe_name, instructions, time_minutes, ingredients):
        flash(f'Recipe "{recipe_name}" updated successfully!', "success")
        return redirect(url_for("view_recipe", recipe_name=recipe_name))
    else:
        flash("Error updating recipe.", "error")
        return redirect(url_for("edit_recipe_form", recipe_name=recipe_name))


@app.route("/recipes/rate/<recipe_name>", methods=["POST"])
@requires_auth
def rate_recipe(recipe_name):
    """Rate a recipe."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    rating = int(request.form.get("rating", 0))

    if user_pantry.rate_recipe(recipe_name, rating):
        flash(f'Recipe "{recipe_name}" rated {rating} stars!', "success")
    else:
        flash("Error rating recipe.", "error")

    return redirect(url_for("view_recipe", recipe_name=recipe_name))


@app.route("/recipes/execute/<recipe_name>", methods=["POST"])
@requires_auth
def execute_recipe(recipe_name):
    """Execute a recipe (remove ingredients from pantry)."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

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
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    # Get current week's meal plan
    start = date.today()
    end = start + timedelta(days=6)
    plan = user_pantry.get_meal_plan(start.isoformat(), end.isoformat())
    recipes_list = user_pantry.get_all_recipes()
    grocery_list = user_pantry.get_grocery_list()

    return render_template(
        "meal_plan.html",
        meal_plan=plan,
        recipes=recipes_list,
        grocery_list=grocery_list,
        start_date=start,
        end_date=end,
    )


@app.route("/meal-plan/set", methods=["POST"])
@requires_auth
def set_meal_plan():
    """Set meal plan for a specific date."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    meal_date = request.form.get("meal_date")
    recipe_name = request.form.get("recipe_name")

    if user_pantry.set_meal_plan(meal_date, recipe_name):
        flash(f"Meal plan updated for {meal_date}!", "success")
    else:
        flash("Error updating meal plan.", "error")

    return redirect(url_for("meal_plan"))


@app.route("/preferences/household-size", methods=["POST"])
@requires_auth
def update_household_size():
    """Update user's household size."""
    if backend == "sqlite":
        flash("Household size preference not available in SQLite mode.", "error")
        return redirect(url_for("preferences"))

    adults = request.form.get("adults")
    children = request.form.get("children")

    try:
        adults = int(adults) if adults else 2
        children = int(children) if children else 0
    except ValueError:
        flash("Please enter valid numbers for household size.", "error")
        return redirect(url_for("preferences"))

    if adults < 1:
        flash("Number of adults must be at least 1.", "error")
        return redirect(url_for("preferences"))

    if children < 0:
        flash("Number of children cannot be negative.", "error")
        return redirect(url_for("preferences"))

    success, message = auth_manager.set_household_size(
        session["user_id"], adults, children
    )

    if success:
        flash("Household size updated successfully!", "success")
    else:
        flash("Error updating household size.", "error")

    return redirect(url_for("preferences"))


@app.context_processor
def inject_globals():
    """Inject global variables into templates."""
    return {
        "backend": backend,
        "requires_auth": backend == "postgresql",
        "current_user": session.get("username") if backend == "postgresql" else None,
        "t": t,  # Translation function for templates
    }


if __name__ == "__main__":
    app.run(debug=True, port=5000)
