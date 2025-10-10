import json
import os
import secrets
import logging
import traceback
from functools import wraps
from pathlib import Path
from i18n import t, set_lang
import i18n
import markdown
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from datetime import date, timedelta, datetime
from pantry_manager_factory import create_pantry_manager
from pantry_manager_shared import SharedPantryManager
from web_auth_simple import WebUserManager
from constants import is_infinite_ingredient
from flask_openrouter_integration import add_openrouter_routes


# Set up comprehensive Flask logging
def setup_flask_logging():
    """Set up detailed Flask application logging."""
    # Get log directory and file from environment
    log_dir = os.getenv("FLASK_LOG_DIR", "logs")
    log_file = os.getenv("FLASK_LOG_FILE", "flask_app.log")

    # Ensure log directory exists
    Path(log_dir).mkdir(exist_ok=True)
    log_path = Path(log_dir) / log_file

    # Create file handler for Flask logs
    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # Create detailed formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)

    # Configure Flask app logger
    flask_logger = logging.getLogger("werkzeug")
    flask_logger.setLevel(logging.DEBUG)
    flask_logger.addHandler(file_handler)

    # Configure our app logger
    app_logger = logging.getLogger("app_flask")
    app_logger.setLevel(logging.DEBUG)
    app_logger.addHandler(file_handler)

    # Add console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    app_logger.addHandler(console_handler)

    return log_path


# Set up logging
FLASK_LOG_PATH = setup_flask_logging()
logger = logging.getLogger("app_flask")


def format_quantity(value):
    """Format numeric quantities by removing unnecessary trailing zeros and decimals."""
    if isinstance(value, str):
        try:
            value = float(value)
        except (ValueError, TypeError):
            return str(value)

    if isinstance(value, (int, float)):
        # Convert to float to handle both int and float inputs
        float_val = float(value)

        # Check if it's a whole number
        if float_val.is_integer():
            return str(int(float_val))
        # Remove trailing zeros from decimal
        return f"{float_val:g}"

    return str(value)


def log_error_with_context(error: Exception, context: str, extra_info: dict = None):
    """Log error with full context and traceback."""
    try:
        tb_str = traceback.format_exc()
        error_msg = f"Flask Error in {context}: {str(error)}"

        if extra_info:
            extra_msg = "\nExtra context: " + json.dumps(
                extra_info, indent=2, default=str
            )
            error_msg += extra_msg

        error_msg += f"\n\nFull traceback:\n{tb_str}"
        logger.error(error_msg)
        logger.info(f"Error logged to: {FLASK_LOG_PATH}")

    except Exception as log_error:
        # Fallback logging
        logger.error(f"Failed to log error properly: {log_error}")
        logger.error(f"Original error in {context}: {error}")


# Generate or load persistent secret key
secret_key = os.getenv("FLASK_SECRET_KEY")
if not secret_key:
    # Try to load from file first
    secret_key_file = ".flask_secret_key"
    try:
        if os.path.exists(secret_key_file):
            with open(secret_key_file, "r") as f:
                secret_key = f.read().strip()
            logger.info("Loaded Flask secret key from file")
        else:
            # Generate new key and save it
            secret_key = secrets.token_urlsafe(32)
            with open(secret_key_file, "w") as f:
                f.write(secret_key)
            # Make file readable only by owner
            os.chmod(secret_key_file, 0o600)
            logger.info("Generated and saved new Flask secret key")
    except Exception as e:
        logger.error(f"Error handling secret key file: {e}")
        # Fallback to temporary key
        secret_key = secrets.token_urlsafe(32)
        logger.warning(
            "Using temporary secret key - sessions will not persist across restarts"
        )
else:
    logger.info("Using Flask secret key from environment variable")


app = Flask(__name__, static_folder="assets")
app.secret_key = secret_key

app.permanent_session_lifetime = timedelta(days=7)  # Sessions last 7 days
app.config["SESSION_PERMANENT"] = True

# Add custom template filters
app.jinja_env.filters["format_quantity"] = format_quantity

# Determine backend mode
backend = os.getenv("PANTRY_BACKEND", "sqlite")
connection_string = os.getenv("PANTRY_DATABASE_URL", "pantry.db")

# Initialize authentication manager
try:
    auth_manager = WebUserManager(backend=backend, connection_string=connection_string)
    logger.info(
        f"Authentication manager initialized successfully for {backend} backend"
    )
except Exception as e:
    logger.error(f"Failed to initialize authentication manager: {e}")
    raise

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

    try:
        user_info = auth_manager.get_user_by_id(session["user_id"])
        if not user_info:
            logger.warning(
                f"User ID {session['user_id']} not found in database, session may be stale"
            )
            return None
    except Exception as e:
        logger.error(f"Database error getting user {session.get('user_id')}: {e}")
        return None

    # Set language based on user preference
    set_lang(user_info.get("preferred_language", "en"))

    # Determine household owner id - defaults to user's own id
    household_id = user_info.get("household_id") or user_info["id"]

    # Use SharedPantryManager scoped to household id for PostgreSQL
    return SharedPantryManager(
        connection_string=connection_string,
        user_id=household_id,
        backend="postgresql",
    )


@app.before_request
def set_language():
    """Set language before each request."""
    # Log incoming request for debugging
    if (
        request.endpoint
        and request.endpoint.startswith("pantry")
        or request.path.startswith("/pantry")
    ):
        logger.info(
            f"Incoming request: {request.method} {request.path} from {request.remote_addr}"
        )
        logger.info(f"Request headers: {dict(request.headers)}")
        if request.method == "POST" and request.form:
            # Log form data but be careful with sensitive information
            form_data = dict(request.form)
            logger.info(f"Form data keys: {list(form_data.keys())}")

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
            logger.info("User not authenticated, redirecting to login")
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))

        # Verify user still exists in database
        try:
            user_info = auth_manager.get_user_by_id(session["user_id"])
            if not user_info:
                logger.warning(
                    f"User ID {session['user_id']} not found in database, clearing session"
                )
                session.clear()
                flash("Your session has expired. Please log in again.", "warning")
                return redirect(url_for("login"))
        except Exception as e:
            logger.error(f"Database error during authentication check: {e}")
            flash("A database error occurred. Please try logging in again.", "error")
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
    except Exception:  # pylint: disable=broad-except
        return date_str


@app.template_filter("localized_date")
def localized_date_filter(date_str, format_type="full"):
    """
    Format date string with localized day/month names.

    Args:
        date_str: ISO date string or date object
        format_type:
            - "full" (Monday, January 15, 2025)
            - "short" (Jan 15)
            - "short_with_year" (Jan 15, 2025)
            - "day" (Monday)
            - "numeric" (10-08-2025)
            - "numeric_short" (10-08)

    Returns:
        Localized date string
    """
    from i18n import get_day_name, get_month_name, get_month_name_short

    try:
        if isinstance(date_str, str):
            date_obj = datetime.fromisoformat(date_str).date()
        else:
            date_obj = date_str

        # Get English names first
        english_day = date_obj.strftime("%A")
        english_month = date_obj.strftime("%B")
        english_month_short = date_obj.strftime("%b")

        # Get localized names
        day_name = get_day_name(english_day)
        month_name = get_month_name(english_month)
        month_name_short = get_month_name_short(english_month_short)

        if format_type == "day":
            return day_name
        elif format_type == "short":
            return f"{month_name_short} {date_obj.day}"
        elif format_type == "short_with_year":
            return f"{month_name_short} {date_obj.day}, {date_obj.year}"
        elif format_type == "full":
            return f"{day_name}, {month_name} {date_obj.day}, {date_obj.year}"
        elif format_type == "numeric":
            return f"{date_obj.month:02d}-{date_obj.day:02d}-{date_obj.year}"
        elif format_type == "numeric_short":
            return f"{date_obj.month:02d}-{date_obj.day:02d}"
        else:
            return date_str
    except Exception:  # pylint: disable=broad-except
        return date_str


@app.template_filter("markdown")
def markdown_filter(text):
    """Convert markdown text to HTML."""
    if not text:
        return ""
    try:
        md = markdown.Markdown(extensions=["nl2br", "fenced_code"])
        return md.convert(text)
    except Exception:
        # Fallback to simple line break conversion if markdown fails
        return text.replace("\n", "<br>")


@app.template_filter("shortdatetime")
def short_datetime_filter(timestamp_str):
    """Format ISO timestamp as '17:36 at 25-12-2025'."""
    if not timestamp_str:
        return ""
    try:
        # Parse the ISO timestamp string
        if isinstance(timestamp_str, str):
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            dt = timestamp_str

        # Format as 'HH:MM at DD-MM-YYYY' with localized 'at'
        time_part = dt.strftime("%H:%M")
        date_part = dt.strftime("%d-%m-%Y")
        return f"{time_part} {t('at')} {date_part}"
    except Exception:
        # Fallback to original string if parsing fails
        return str(timestamp_str)


# Add OpenRouter routes for LLM functionality
add_openrouter_routes(app, requires_auth)

# Store backend in app config for OpenRouter integration
app.config["PANTRY_BACKEND"] = backend


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
            session.permanent = True  # Make session permanent
            session["user_id"] = user_info["id"]
            session["username"] = user_info["username"]
            session["is_first_login"] = user_info.get("is_first_login", False)
            session["is_admin"] = user_info.get("is_admin", False)
            logger.info(
                f"User {user_info['username']} logged in successfully (first login: {user_info.get('is_first_login', False)}, admin: {user_info.get('is_admin', False)})"
            )
            return redirect(url_for("index"))
        flash("Invalid username or password.", "error")

    return render_template("auth/login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration page."""
    if backend == "sqlite":
        return redirect(url_for("index"))

    invite_code = request.args.get("invite_code", "")
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        language = request.form.get("language", "en")
        invite_code = request.form.get("invite_code", "")

        if not all([username, email, password, confirm_password]):
            flash("Please fill in all fields.", "error")
            return render_template("auth/register.html", invite_code=invite_code)

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html", invite_code=invite_code)

        if language not in ["en", "nl"]:
            language = "en"  # Default to English if invalid language

        success, message = auth_manager.create_user(
            username, email, password, language, invite_code or None
        )

        if success:
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))
        flash(message, "error")
        return render_template("auth/register.html", invite_code=invite_code)

    return render_template("auth/register.html", invite_code=invite_code)


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


@app.route("/invite", methods=["GET", "POST"])
@requires_auth
def invite():
    """Allow household owners to invite others via email."""
    if backend == "sqlite":
        return redirect(url_for("index"))

    user_info = auth_manager.get_user_by_id(session["user_id"])
    if user_info.get("household_id") != user_info["id"]:
        flash("Only household owners can send invites.", "error")
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email")
        if not email:
            flash("Please provide an email address.", "error")
            return render_template("auth/invite.html")

        secret = auth_manager.create_household_invite(user_info["id"], email)
        if secret:
            flash("Invite sent!", "success")
        else:
            flash("Error sending invite.", "error")

    return render_template("auth/invite.html")


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


# Units Management Routes
@app.route("/units")
@requires_auth
def units_management():
    """Units management page."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    units = user_pantry.list_units()
    return render_template("units.html", units=units)


@app.route("/units/add", methods=["POST"])
@requires_auth
def add_unit():
    """Add or update a custom unit."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    name = request.form.get("name", "").strip()
    base_unit = request.form.get("base_unit", "").strip()
    size = request.form.get("size", "").strip()

    if not all([name, base_unit, size]):
        flash("Please fill in all fields.", "error")
        return redirect(url_for("units_management"))

    try:
        size_float = float(size)
        if size_float <= 0:
            flash("Size must be a positive number.", "error")
            return redirect(url_for("units_management"))
    except ValueError:
        flash("Size must be a valid number.", "error")
        return redirect(url_for("units_management"))

    if user_pantry.set_unit(name, base_unit, size_float):
        flash(f"Unit '{name}' added/updated successfully!", "success")
    else:
        flash(f"Failed to add/update unit '{name}'.", "error")

    return redirect(url_for("units_management"))


@app.route("/units/delete", methods=["POST"])
@requires_auth
def delete_unit():
    """Delete a custom unit."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    name = request.form.get("name", "").strip()
    if not name:
        flash("Unit name is required.", "error")
        return redirect(url_for("units_management"))

    if user_pantry.delete_unit(name):
        flash(f"Unit '{name}' deleted successfully!", "success")
    else:
        flash(f"Cannot delete unit '{name}' - it may be in use or not exist.", "error")

    return redirect(url_for("units_management"))


@app.route("/")
def index():
    """Main dashboard or landing page."""
    if backend == "sqlite":
        # For SQLite mode, go directly to dashboard
        context = {"backend": backend, "is_first_login": False, "is_admin": False}
        return render_template("index.html", **context)

    if "user_id" in session:
        # User is logged in, show dashboard
        context = {"backend": backend}
        if "username" in session:
            context["username"] = session["username"]
        # Get and clear is_first_login flag (only show once)
        context["is_first_login"] = session.pop("is_first_login", False)
        context["is_admin"] = session.get("is_admin", False)
        return render_template("index.html", **context)

    # User is not logged in, show landing page
    return render_template("landing.html")


@app.route("/dashboard")
@requires_auth
def dashboard():
    """Main dashboard page (protected)."""
    context = {"backend": backend, "is_first_login": False}
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

    # Get current user info for household size and goals
    current_user_info = None
    household_goals = None
    if backend == "postgresql" and "user_id" in session:
        current_user_info = auth_manager.get_user_by_id(session["user_id"])
        household_goals = auth_manager.get_household_goals(session["user_id"])

    return render_template(
        "preferences.html",
        preferences=prefs,
        current_user_info=current_user_info,
        household_goals=household_goals,
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
    units = [u["name"] for u in user_pantry.list_units()]
    return render_template(
        "pantry.html", contents=contents, transactions=transactions, units=units
    )


@app.route("/pantry/add", methods=["POST"])
@requires_auth
def add_pantry_item():
    """Add item to pantry."""
    # Log incoming request details
    request_info = {
        "method": request.method,
        "form_data": dict(request.form),
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "backend": backend,
        "endpoint": "/pantry/add",
    }
    logger.info(f"Pantry add request started: {json.dumps(request_info, indent=2)}")

    # pylint: disable=line-too-long
    try:
        user_pantry = get_current_user_pantry()
        if not user_pantry:
            logger.error("Failed to get user pantry in add_pantry_item")
            flash("Unable to access your data. Please try logging in again.", "error")
            return redirect(url_for("logout"))

        # Extract and validate form data
        item_name = request.form.get("item_name")
        quantity_str = request.form.get("quantity", "0")
        unit = request.form.get("unit")
        notes = request.form.get("notes", "")

        logger.info(
            f"Extracted form data - item_name: '{item_name}', quantity: '{quantity_str}', unit: '{unit}', notes: '{notes}'"
        )

        # Validate required fields
        if not item_name or not item_name.strip():
            logger.warning("Empty item name provided")
            flash("Item name is required.", "error")
            return redirect(url_for("pantry_view"))

        if not unit or not unit.strip():
            logger.warning("Empty unit provided")
            flash("Unit is required.", "error")
            return redirect(url_for("pantry_view"))

        # Parse and validate quantity
        try:
            quantity = float(quantity_str)
            if quantity <= 0:
                logger.warning(f"Invalid quantity provided: {quantity}")
                flash("Quantity must be greater than 0.", "error")
                return redirect(url_for("pantry_view"))
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse quantity '{quantity_str}': {e}")
            flash("Please enter a valid number for quantity.", "error")
            return redirect(url_for("pantry_view"))

        logger.info(
            f"Attempting to add item: name='{item_name}', quantity={quantity}, unit='{unit}', notes='{notes}'"
        )

        # Attempt to add the item
        success = user_pantry.add_item(item_name, quantity, unit, notes)

        if success:
            logger.info(
                f"Successfully added {quantity} {unit} of {item_name} to pantry"
            )
            flash(f"Added {quantity} {unit} of {item_name} to pantry!", "success")
        else:
            logger.error(
                f"Failed to add item to pantry - add_item returned False for: name='{item_name}', quantity={quantity}, unit='{unit}'"
            )
            flash("Error adding item to pantry.", "error")

        return redirect(url_for("pantry_view"))

    except Exception as e:
        log_error_with_context(
            e,
            "add_pantry_item",
            {
                "form_data": dict(request.form),
                "user_session": {
                    "user_id": session.get("user_id"),
                    "username": session.get("username"),
                },
                "backend": backend,
            },
        )
        flash("An unexpected error occurred while adding the item.", "error")
        return redirect(url_for("pantry_view"))


@app.route("/pantry/remove", methods=["POST"])
@requires_auth
def remove_pantry_item():
    """Remove item from pantry."""
    # Log incoming request details
    request_info = {
        "method": request.method,
        "form_data": dict(request.form),
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "backend": backend,
        "endpoint": "/pantry/remove",
    }
    logger.info(f"Pantry remove request started: {json.dumps(request_info, indent=2)}")

    # pylint: disable=line-too-long
    try:
        user_pantry = get_current_user_pantry()
        if not user_pantry:
            logger.error("Failed to get user pantry in remove_pantry_item")
            flash("Unable to access your data. Please try logging in again.", "error")
            return redirect(url_for("logout"))

        # Extract and validate form data
        item_name = request.form.get("item_name")
        quantity_str = request.form.get("quantity", "0")
        unit = request.form.get("unit")
        notes = request.form.get("notes", "")

        logger.info(
            f"Extracted form data - item_name: '{item_name}', quantity: '{quantity_str}', unit: '{unit}', notes: '{notes}'"
        )

        # Validate required fields
        if not item_name or not item_name.strip():
            logger.warning("Empty item name provided")
            flash("Item name is required.", "error")
            return redirect(url_for("pantry_view"))

        if not unit or not unit.strip():
            logger.warning("Empty unit provided")
            flash("Unit is required.", "error")
            return redirect(url_for("pantry_view"))

        # Parse and validate quantity
        try:
            quantity = float(quantity_str)
            if quantity <= 0:
                logger.warning(f"Invalid quantity provided: {quantity}")
                flash("Quantity must be greater than 0.", "error")
                return redirect(url_for("pantry_view"))
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse quantity '{quantity_str}': {e}")
            flash("Please enter a valid number for quantity.", "error")
            return redirect(url_for("pantry_view"))

        logger.info(
            f"Attempting to remove item: name='{item_name}', quantity={quantity}, unit='{unit}', notes='{notes}'"
        )

        # Attempt to remove the item
        success = user_pantry.remove_item(item_name, quantity, unit, notes)

        if success:
            logger.info(
                f"Successfully removed {quantity} {unit} of {item_name} from pantry"
            )
            flash(f"Removed {quantity} {unit} of {item_name} from pantry!", "success")
        else:
            logger.error(
                f"Failed to remove item from pantry - remove_item returned False for: name='{item_name}', quantity={quantity}, unit='{unit}'"
            )
            flash("Error removing item from pantry.", "error")

        return redirect(url_for("pantry_view"))

    except Exception as e:
        log_error_with_context(
            e,
            "remove_pantry_item",
            {
                "form_data": dict(request.form),
                "user_session": {
                    "user_id": session.get("user_id"),
                    "username": session.get("username"),
                },
                "backend": backend,
            },
        )
        flash("An unexpected error occurred while removing the item.", "error")
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

    # Calculate missing ingredients
    missing_ingredients = []
    available_ingredients = []

    for ingredient in recipe["ingredients"]:
        needed_quantity = ingredient["quantity"]
        ingredient_name = ingredient["name"]

        # Skip infinite ingredients entirely (e.g., water, salt) - users know
        # these are always available
        if is_infinite_ingredient(ingredient_name, i18n.LANG):
            continue

        available_quantity = user_pantry.get_total_item_quantity(
            ingredient_name, ingredient["unit"]
        )

        if available_quantity < needed_quantity:
            missing_ingredients.append(
                {
                    "name": ingredient_name,
                    "needed": format_quantity(needed_quantity),
                    "available": format_quantity(available_quantity),
                    "missing": format_quantity(needed_quantity - available_quantity),
                    "unit": ingredient["unit"],
                }
            )
        else:
            available_ingredients.append(
                {
                    "name": ingredient_name,
                    "needed": format_quantity(needed_quantity),
                    "available": format_quantity(available_quantity),
                    "unit": ingredient["unit"],
                }
            )

    return render_template(
        "recipe_view.html",
        recipe=recipe,
        missing_ingredients=missing_ingredients,
        available_ingredients=available_ingredients,
    )


@app.route("/recipes/add")
@requires_auth
def add_recipe_form():
    """Show add recipe form."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))
    units = [u["name"] for u in user_pantry.list_units()]
    return render_template("recipe_add.html", units=units)


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
    servings = int(request.form.get("servings", 4))

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

    if user_pantry.add_recipe(name, instructions, time_minutes, ingredients, servings):
        flash(t('Recipe "{name}" added successfully!').format(name=name), "success")
        return redirect(url_for("recipes"))
    flash(t("Error adding recipe."), "error")
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
    units = [u["name"] for u in user_pantry.list_units()]
    return render_template("recipe_edit.html", recipe=recipe, units=units)


@app.route("/recipes/edit/<recipe_name>", methods=["POST"])
@requires_auth
def edit_recipe(recipe_name):
    """Edit an existing recipe."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    new_name = request.form.get("name", "").strip()
    instructions = request.form.get("instructions")
    time_minutes = int(request.form.get("time_minutes", 0))
    servings = int(request.form.get("servings", 4))

    # Use new name if provided and different, otherwise None
    name_to_update = new_name if new_name and new_name != recipe_name else None

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

    if user_pantry.edit_recipe(
        recipe_name,
        instructions,
        time_minutes,
        ingredients,
        new_name=name_to_update,
        servings=servings,
    ):
        # Use the new name if it was changed, otherwise use the original
        final_name = name_to_update if name_to_update else recipe_name
        flash(
            t('Recipe "{name}" updated successfully!').format(name=final_name),
            "success",
        )
        return redirect(url_for("view_recipe", recipe_name=final_name))
    flash(t("Error updating recipe."), "error")
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
        flash(
            t('Recipe "{name}" rated {rating} stars!').format(
                name=recipe_name, rating=rating
            ),
            "success",
        )
    else:
        flash(t("Error rating recipe."), "error")

    return redirect(url_for("view_recipe", recipe_name=recipe_name))


@app.route("/recipes/delete/<recipe_name>", methods=["POST"])
@requires_auth
def delete_recipe(recipe_name):
    """Delete a recipe."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    if user_pantry.delete_recipe(recipe_name):
        flash(
            t('Recipe "{name}" deleted successfully!').format(name=recipe_name),
            "success",
        )
        return redirect(url_for("recipes"))
    else:
        flash(t("Error deleting recipe."), "error")
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
        flash(t("Meal plan updated for {date}!").format(date=meal_date), "success")
    else:
        flash(t("Error updating meal plan."), "error")

    return redirect(url_for("meal_plan"))


@app.route("/meal-plan/clear", methods=["POST"])
@requires_auth
def clear_meal_plan():
    """Clear meal plan for a specific date."""
    user_pantry = get_current_user_pantry()
    if not user_pantry:
        flash("Unable to access your data. Please try logging in again.", "error")
        return redirect(url_for("logout"))

    meal_date = request.form.get("meal_date")

    if user_pantry.clear_recipe_for_date(meal_date):
        flash(t("Meal cleared for {date}!").format(date=meal_date), "success")
    else:
        flash(t("Error clearing meal plan."), "error")

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

    success, _ = auth_manager.set_household_size(session["user_id"], adults, children)

    if success:
        flash("Household size updated successfully!", "success")
    else:
        flash("Error updating household size.", "error")

    return redirect(url_for("preferences"))


@app.route("/preferences/household-goals", methods=["POST"])
@requires_auth
def update_household_goals():
    """Update user's household goals/preferences."""
    if backend == "sqlite":
        flash(t("Household goals not available in SQLite mode."), "error")
        return redirect(url_for("preferences"))

    goals = request.form.get("goals", "").strip()

    success, _ = auth_manager.set_household_goals(session["user_id"], goals)

    if success:
        flash(t("Household goals updated successfully!"), "success")
    else:
        flash(t("Error updating household goals."), "error")

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
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    app.run(debug=True, port=port, host="0.0.0.0")
