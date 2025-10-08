// Shared recipe form functionality

// Initialize and categorize units
function initializeRecipeUnits(allUnits) {
    window.recipeUnits = allUnits;
    window.recipeUnitsByCategory = {
        common: [],
        volume: [],
        weight: [],
        other: []
    };

    // Organize units by category
    ['Teaspoon', 'Tablespoon', 'Cup', 'Gram', 'Ounce', 'Piece'].forEach(unit => {
        if (allUnits.includes(unit)) window.recipeUnitsByCategory.common.push(unit);
    });
    ['Milliliter', 'Liter', 'Fluid ounce', 'Pint', 'Quart', 'Gallon'].forEach(unit => {
        if (allUnits.includes(unit)) window.recipeUnitsByCategory.volume.push(unit);
    });
    ['Kilogram', 'Pound'].forEach(unit => {
        if (allUnits.includes(unit)) window.recipeUnitsByCategory.weight.push(unit);
    });

    // Calculate other units (those not in any other category)
    const allCategorizedUnits = [
        ...window.recipeUnitsByCategory.common,
        ...window.recipeUnitsByCategory.volume,
        ...window.recipeUnitsByCategory.weight
    ];
    window.recipeUnitsByCategory.other = allUnits.filter(unit => !allCategorizedUnits.includes(unit));
}

// Build units dropdown options
function buildUnitsOptions() {
    if (typeof window.recipeUnitsByCategory === 'undefined') {
        console.warn('Recipe units not initialized');
        return '<option value="">Unit</option>';
    }

    const cats = window.recipeUnitsByCategory;
    const labels = window.recipeLabels || {};
    let options = '<option value="">' + (labels.selectUnit || 'Select unit...') + '</option>';

    // Common Cooking Units
    if (cats.common && cats.common.length > 0) {
        options += '<optgroup label="🍽️ ' + (labels.common || 'Common Cooking') + '">';
        cats.common.forEach(unit => {
            options += `<option value="${unit}">${unit}</option>`;
        });
        options += '</optgroup>';
    }

    // Volume Units
    if (cats.volume && cats.volume.length > 0) {
        options += '<optgroup label="🥤 ' + (labels.volume || 'Volume') + '">';
        cats.volume.forEach(unit => {
            options += `<option value="${unit}">${unit}</option>`;
        });
        options += '</optgroup>';
    }

    // Weight Units
    if (cats.weight && cats.weight.length > 0) {
        options += '<optgroup label="⚖️ ' + (labels.weight || 'Weight') + '">';
        cats.weight.forEach(unit => {
            options += `<option value="${unit}">${unit}</option>`;
        });
        options += '</optgroup>';
    }

    // Other Units
    if (cats.other && cats.other.length > 0) {
        options += '<optgroup label="📦 ' + (labels.other || 'Other') + '">';
        cats.other.forEach(unit => {
            options += `<option value="${unit}">${unit}</option>`;
        });
        options += '</optgroup>';
    }

    return options;
}

// Add a new ingredient row to the form
function addIngredient() {
    const container = document.getElementById('ingredients-container');
    const newRow = document.createElement('div');
    newRow.className = 'ingredient-row mb-2';

    newRow.innerHTML = `
        <div class="row">
            <div class="col-md-4">
                <input type="text" class="form-control" name="ingredient_name[]"
                       placeholder="Ingredient name" required>
            </div>
            <div class="col-md-3">
                <input type="number" class="form-control" name="ingredient_quantity[]"
                       placeholder="Quantity" step="0.01" required>
            </div>
            <div class="col-md-3">
                <select class="form-select" name="ingredient_unit[]" required>
                    ${buildUnitsOptions()}
                </select>
            </div>
            <div class="col-md-2">
                <button type="button" class="btn btn-outline-danger w-100" onclick="removeIngredient(this)">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `;
    container.appendChild(newRow);
}

// Remove an ingredient row from the form
function removeIngredient(button) {
    const ingredientRow = button.closest('.ingredient-row');
    const container = document.getElementById('ingredients-container');

    // Don't remove if it's the last ingredient
    if (container.children.length > 1) {
        ingredientRow.remove();
    } else {
        // Clear the inputs instead of removing the row
        const inputs = ingredientRow.querySelectorAll('input, select');
        inputs.forEach(input => {
            input.value = '';
        });
    }
}
