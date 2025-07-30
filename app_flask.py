from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pantry_manager_factory import create_pantry_manager
from constants import UNITS
from i18n import t
from datetime import date, timedelta, datetime
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this in production

# Initialize pantry manager
pantry = create_pantry_manager()

# Custom Jinja2 filters
@app.template_filter('strftime')
def strftime_filter(date_str, format='%A'):
    """Format date string."""
    try:
        if isinstance(date_str, str):
            date_obj = datetime.fromisoformat(date_str).date()
        else:
            date_obj = date_str
        return date_obj.strftime(format)
    except:
        return date_str

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')

@app.route('/preferences')
def preferences():
    """Preferences management page."""
    prefs = pantry.get_preferences()
    return render_template('preferences.html', preferences=prefs)

@app.route('/preferences/add', methods=['POST'])
def add_preference():
    """Add a new preference."""
    category = request.form.get('category')
    item = request.form.get('item')
    level = request.form.get('level')
    notes = request.form.get('notes', '')
    
    if pantry.add_preference(category, item, level, notes):
        flash('Preference added successfully!', 'success')
    else:
        flash('Error adding preference.', 'error')
    
    return redirect(url_for('preferences'))

@app.route('/preferences/delete/<int:pref_id>')
def delete_preference(pref_id):
    """Delete a preference."""
    if pantry.delete_preference(pref_id):
        flash('Preference deleted successfully!', 'success')
    else:
        flash('Error deleting preference.', 'error')
    
    return redirect(url_for('preferences'))

@app.route('/pantry')
def pantry_view():
    """Pantry management page."""
    contents = pantry.get_pantry_contents()
    transactions = pantry.get_transaction_history()
    return render_template('pantry.html', contents=contents, transactions=transactions, units=UNITS)

@app.route('/pantry/add', methods=['POST'])
def add_pantry_item():
    """Add item to pantry."""
    item_name = request.form.get('item_name')
    quantity = float(request.form.get('quantity', 0))
    unit = request.form.get('unit')
    notes = request.form.get('notes', '')
    
    if pantry.add_item(item_name, quantity, unit, notes):
        flash(f'Added {quantity} {unit} of {item_name} to pantry!', 'success')
    else:
        flash('Error adding item to pantry.', 'error')
    
    return redirect(url_for('pantry_view'))

@app.route('/pantry/remove', methods=['POST'])
def remove_pantry_item():
    """Remove item from pantry."""
    item_name = request.form.get('item_name')
    quantity = float(request.form.get('quantity', 0))
    unit = request.form.get('unit')
    notes = request.form.get('notes', '')
    
    if pantry.remove_item(item_name, quantity, unit, notes):
        flash(f'Removed {quantity} {unit} of {item_name} from pantry!', 'success')
    else:
        flash('Error removing item from pantry.', 'error')
    
    return redirect(url_for('pantry_view'))

@app.route('/recipes')
def recipes():
    """Recipe management page."""
    recipes_list = pantry.get_all_recipes()
    return render_template('recipes.html', recipes=recipes_list)

@app.route('/recipes/view/<recipe_name>')
def view_recipe(recipe_name):
    """View a specific recipe."""
    recipe = pantry.get_recipe(recipe_name)
    if not recipe:
        flash('Recipe not found.', 'error')
        return redirect(url_for('recipes'))
    return render_template('recipe_view.html', recipe=recipe)

@app.route('/recipes/add')
def add_recipe_form():
    """Show add recipe form."""
    return render_template('recipe_add.html', units=UNITS)

@app.route('/recipes/add', methods=['POST'])
def add_recipe():
    """Add a new recipe."""
    name = request.form.get('name')
    instructions = request.form.get('instructions')
    time_minutes = int(request.form.get('time_minutes', 0))
    
    # Parse ingredients from form
    ingredients = []
    ingredient_names = request.form.getlist('ingredient_name[]')
    ingredient_quantities = request.form.getlist('ingredient_quantity[]')
    ingredient_units = request.form.getlist('ingredient_unit[]')
    
    for i in range(len(ingredient_names)):
        if ingredient_names[i]:  # Skip empty ingredient names
            ingredients.append({
                'name': ingredient_names[i],
                'quantity': float(ingredient_quantities[i]),
                'unit': ingredient_units[i]
            })
    
    if pantry.add_recipe(name, instructions, time_minutes, ingredients):
        flash(f'Recipe "{name}" added successfully!', 'success')
        return redirect(url_for('recipes'))
    else:
        flash('Error adding recipe.', 'error')
        return redirect(url_for('add_recipe_form'))

@app.route('/recipes/edit/<recipe_name>')
def edit_recipe_form(recipe_name):
    """Show edit recipe form."""
    recipe = pantry.get_recipe(recipe_name)
    if not recipe:
        flash('Recipe not found.', 'error')
        return redirect(url_for('recipes'))
    return render_template('recipe_edit.html', recipe=recipe, units=UNITS)

@app.route('/recipes/edit/<recipe_name>', methods=['POST'])
def edit_recipe(recipe_name):
    """Edit an existing recipe."""
    instructions = request.form.get('instructions')
    time_minutes = int(request.form.get('time_minutes', 0))
    
    # Parse ingredients from form
    ingredients = []
    ingredient_names = request.form.getlist('ingredient_name[]')
    ingredient_quantities = request.form.getlist('ingredient_quantity[]')
    ingredient_units = request.form.getlist('ingredient_unit[]')
    
    for i in range(len(ingredient_names)):
        if ingredient_names[i]:  # Skip empty ingredient names
            ingredients.append({
                'name': ingredient_names[i],
                'quantity': float(ingredient_quantities[i]),
                'unit': ingredient_units[i]
            })
    
    if pantry.edit_recipe(recipe_name, instructions, time_minutes, ingredients):
        flash(f'Recipe "{recipe_name}" updated successfully!', 'success')
        return redirect(url_for('view_recipe', recipe_name=recipe_name))
    else:
        flash('Error updating recipe.', 'error')
        return redirect(url_for('edit_recipe_form', recipe_name=recipe_name))

@app.route('/recipes/rate/<recipe_name>', methods=['POST'])
def rate_recipe(recipe_name):
    """Rate a recipe."""
    rating = int(request.form.get('rating', 0))
    
    if pantry.rate_recipe(recipe_name, rating):
        flash(f'Recipe "{recipe_name}" rated {rating} stars!', 'success')
    else:
        flash('Error rating recipe.', 'error')
    
    return redirect(url_for('view_recipe', recipe_name=recipe_name))

@app.route('/recipes/execute/<recipe_name>', methods=['POST'])
def execute_recipe(recipe_name):
    """Execute a recipe (remove ingredients from pantry)."""
    success, message = pantry.execute_recipe(recipe_name)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('view_recipe', recipe_name=recipe_name))

@app.route('/meal-plan')
def meal_plan():
    """Meal planning page."""
    # Get current week's meal plan
    start = date.today()
    end = start + timedelta(days=6)
    plan = pantry.get_meal_plan(start.isoformat(), end.isoformat())
    recipes_list = pantry.get_all_recipes()
    grocery_list = pantry.get_grocery_list()
    
    return render_template('meal_plan.html', 
                         meal_plan=plan, 
                         recipes=recipes_list, 
                         grocery_list=grocery_list,
                         start_date=start,
                         end_date=end)

@app.route('/meal-plan/set', methods=['POST'])
def set_meal_plan():
    """Set meal plan for a specific date."""
    meal_date = request.form.get('meal_date')
    recipe_name = request.form.get('recipe_name')
    
    if pantry.set_meal_plan(meal_date, recipe_name):
        flash(f'Meal plan updated for {meal_date}!', 'success')
    else:
        flash('Error updating meal plan.', 'error')
    
    return redirect(url_for('meal_plan'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)