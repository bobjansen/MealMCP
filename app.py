from dash import (
    ALL,
    Dash,
    Input,
    Output,
    State,
    dash_table,
    dcc,
    html,
    callback_context,
)
import dash_bootstrap_components as dbc
from pantry_manager import PantryManager

# Initialize the Dash app with Bootstrap theme
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
pantry = PantryManager()


# Layout components
def create_preferences_layout():
    """Create the layout for the preferences page."""
    return html.Div(
        [
            dbc.Card(
                [
                    dbc.CardHeader("Food Preferences"),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Form(
                                                [
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    dbc.Label(
                                                                        "Category"
                                                                    ),
                                                                    dcc.Dropdown(
                                                                        id="pref-category",
                                                                        options=[
                                                                            {
                                                                                "label": "Dietary Restriction",
                                                                                "value": "dietary",
                                                                            },
                                                                            {
                                                                                "label": "Allergy",
                                                                                "value": "allergy",
                                                                            },
                                                                            {
                                                                                "label": "Dislike",
                                                                                "value": "dislike",
                                                                            },
                                                                        ],
                                                                        placeholder="Select category",
                                                                    ),
                                                                ],
                                                                width=3,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Label("Item"),
                                                                    dbc.Input(
                                                                        id="pref-item",
                                                                        type="text",
                                                                        placeholder="Enter item (e.g., vegetarian, peanuts)",
                                                                    ),
                                                                ],
                                                                width=3,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Label("Level"),
                                                                    dcc.Dropdown(
                                                                        id="pref-level",
                                                                        options=[
                                                                            {
                                                                                "label": "Required",
                                                                                "value": "required",
                                                                            },
                                                                            {
                                                                                "label": "Preferred",
                                                                                "value": "preferred",
                                                                            },
                                                                            {
                                                                                "label": "Avoid",
                                                                                "value": "avoid",
                                                                            },
                                                                        ],
                                                                        placeholder="Select level",
                                                                    ),
                                                                ],
                                                                width=3,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Label("Notes"),
                                                                    dbc.Input(
                                                                        id="pref-notes",
                                                                        type="text",
                                                                        placeholder="Optional notes",
                                                                    ),
                                                                ],
                                                                width=3,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    dbc.Row(
                                                        dbc.Col(
                                                            dbc.Button(
                                                                "Add Preference",
                                                                id="add-preference-btn",
                                                                color="primary",
                                                            ),
                                                            width="auto",
                                                        )
                                                    ),
                                                ]
                                            ),
                                        ]
                                    )
                                ]
                            ),
                            html.Hr(),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.H4("Current Preferences"),
                                            dash_table.DataTable(
                                                id="preferences-table",
                                                columns=[
                                                    {
                                                        "name": "Category",
                                                        "id": "category",
                                                    },
                                                    {"name": "Item", "id": "item"},
                                                    {"name": "Level", "id": "level"},
                                                    {"name": "Notes", "id": "notes"},
                                                ],
                                                data=[],
                                                style_cell={
                                                    "textAlign": "left",
                                                    "padding": "10px",
                                                },
                                                style_header={
                                                    "backgroundColor": "rgb(230, 230, 230)",
                                                    "fontWeight": "bold",
                                                },
                                                row_deletable=True,
                                            ),
                                        ]
                                    )
                                ]
                            ),
                        ]
                    ),
                ]
            )
        ]
    )


def create_make_recipe_layout():
    return html.Div(
        [
            dbc.Card(
                [
                    dbc.CardHeader("Make Recipe"),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Select Recipe"),
                                            dcc.Dropdown(
                                                id="recipe-select",
                                                options=[],
                                                placeholder="Choose a recipe",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Scale Factor"),
                                            dbc.Input(
                                                id="scale-factor",
                                                type="number",
                                                value=1,
                                                min=0.1,
                                                step=0.1,
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Br(),
                                            dbc.Button(
                                                "Make Recipe",
                                                id="make-recipe-button",
                                                color="primary",
                                                className="mt-2",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                ]
                            ),
                            html.Div(id="recipe-details", className="mt-4"),
                            html.Div(id="make-recipe-message", className="mt-3"),
                        ]
                    ),
                ],
                className="mb-4",
            ),
        ]
    )


def create_recipe_layout():
    return html.Div(
        [
            # Edit Recipe Modal
            dbc.Modal(
                [
                    dbc.ModalHeader("Edit Recipe"),
                    dbc.ModalBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Preparation Time (minutes)"),
                                            dbc.Input(
                                                id="edit-prep-time",
                                                type="number",
                                                placeholder="Enter preparation time",
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Instructions"),
                                            dbc.Textarea(
                                                id="edit-instructions",
                                                placeholder="Enter cooking instructions",
                                                style={"height": "150px"},
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Div(
                                [
                                    html.H5("Ingredients", className="mb-3"),
                                    html.Div(
                                        id="edit-ingredient-list",
                                        children=[],
                                    ),
                                    dbc.Button(
                                        "Add Ingredient",
                                        id="edit-add-ingredient-row",
                                        color="secondary",
                                        size="sm",
                                        className="mt-2",
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel", id="edit-recipe-close", className="me-2"
                            ),
                            dbc.Button(
                                "Save Changes",
                                id="edit-recipe-save",
                                color="primary",
                            ),
                        ]
                    ),
                ],
                id="edit-recipe-modal",
                size="lg",
            ),
            dbc.Card(
                [
                    dbc.CardHeader("Add New Recipe"),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Recipe Name"),
                                            dbc.Input(
                                                id="recipe-name",
                                                type="text",
                                                placeholder="Enter recipe name",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Preparation Time (minutes)"),
                                            dbc.Input(
                                                id="prep-time",
                                                type="number",
                                                placeholder="Enter preparation time",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Instructions"),
                                            dbc.Textarea(
                                                id="instructions",
                                                placeholder="Enter cooking instructions",
                                                style={"height": "150px"},
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Div(
                                [
                                    html.H5("Ingredients", className="mb-3"),
                                    html.Div(
                                        id="ingredient-list",
                                        children=[
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Input(
                                                                id={
                                                                    "type": "ingredient-name",
                                                                    "index": 0,
                                                                },
                                                                type="text",
                                                                placeholder="Ingredient name",
                                                            ),
                                                        ],
                                                        width=4,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Input(
                                                                id={
                                                                    "type": "ingredient-quantity",
                                                                    "index": 0,
                                                                },
                                                                type="number",
                                                                placeholder="Quantity",
                                                            ),
                                                        ],
                                                        width=3,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Input(
                                                                id={
                                                                    "type": "ingredient-unit",
                                                                    "index": 0,
                                                                },
                                                                type="text",
                                                                placeholder="Unit",
                                                            ),
                                                        ],
                                                        width=3,
                                                    ),
                                                ],
                                                className="mb-2",
                                            ),
                                        ],
                                    ),
                                    dbc.Button(
                                        "Add Ingredient",
                                        id="add-ingredient-row",
                                        color="secondary",
                                        size="sm",
                                        className="mt-2",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Button(
                                "Save Recipe", id="save-recipe", color="primary"
                            ),
                            html.Div(id="recipe-message", className="mt-3"),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            dbc.Card(
                [
                    dbc.CardHeader("Saved Recipes"),
                    dbc.CardBody(
                        [
                            html.Div(id="recipe-list"),
                            dbc.Button(
                                "Refresh Recipes",
                                id="refresh-recipes",
                                color="secondary",
                                className="mb-3",
                            ),
                            html.Div(
                                id="recipe-cards",
                                className="mt-3",
                            ),
                        ]
                    ),
                ]
            ),
        ]
    )


def create_pantry_layout():
    return html.Div(
        [
            dbc.Card(
                [
                    dbc.CardHeader("Add Item to Pantry"),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Item Name"),
                                            dbc.Input(
                                                id="item-name",
                                                type="text",
                                                placeholder="Enter item name",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Quantity"),
                                            dbc.Input(
                                                id="quantity",
                                                type="number",
                                                placeholder="Enter quantity",
                                            ),
                                        ],
                                        width=2,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Unit"),
                                            dbc.Input(
                                                id="unit",
                                                type="text",
                                                placeholder="e.g., g, kg, ml",
                                            ),
                                        ],
                                        width=2,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Notes"),
                                            dbc.Input(
                                                id="notes",
                                                type="text",
                                                placeholder="Optional notes",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Br(),
                                            dbc.Button(
                                                "Add Item",
                                                id="add-button",
                                                color="primary",
                                                className="mt-2",
                                            ),
                                        ],
                                        width=2,
                                    ),
                                ]
                            ),
                            html.Div(id="add-message", className="mt-3"),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # Current Pantry Contents
            dbc.Card(
                [
                    dbc.CardHeader("Current Pantry Contents"),
                    dbc.CardBody(
                        [
                            html.Div(id="pantry-contents"),
                            dbc.Button(
                                "Refresh",
                                id="refresh-button",
                                color="secondary",
                                className="mt-3",
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # Transaction History
            dbc.Card(
                [
                    dbc.CardHeader("Transaction History"),
                    dbc.CardBody(
                        [
                            dash_table.DataTable(
                                id="transaction-table",
                                columns=[
                                    {"name": "Date", "id": "transaction_date"},
                                    {"name": "Type", "id": "transaction_type"},
                                    {"name": "Item", "id": "item_name"},
                                    {"name": "Quantity", "id": "quantity"},
                                    {"name": "Unit", "id": "unit"},
                                    {"name": "Notes", "id": "notes"},
                                ],
                                style_table={"overflowX": "auto"},
                                style_cell={
                                    "textAlign": "left",
                                    "padding": "10px",
                                    "whiteSpace": "normal",
                                    "height": "auto",
                                },
                                style_header={
                                    "backgroundColor": "rgb(230, 230, 230)",
                                    "fontWeight": "bold",
                                },
                                page_size=10,
                            )
                        ]
                    ),
                ]
            ),
        ]
    )


# App layout with tabs
app.layout = dbc.Container(
    [
        html.H1("Meal Planner", className="my-4"),
        dbc.Tabs(
            [
                dbc.Tab(
                    create_pantry_layout(), label="Pantry Management", tab_id="pantry"
                ),
                dbc.Tab(create_recipe_layout(), label="Recipes", tab_id="recipes"),
                dbc.Tab(
                    create_make_recipe_layout(),
                    label="Make Recipe",
                    tab_id="make-recipe",
                ),
                dbc.Tab(
                    create_preferences_layout(),
                    label="Preferences",
                    tab_id="preferences",
                ),
            ],
            id="tabs",
            active_tab="pantry",
        ),
    ],
    fluid=True,
)


# Callback to display recipes
@app.callback(
    Output("recipe-list", "children"),
    [Input("refresh-recipes", "n_clicks"), Input("recipe-message", "children")],
)
def update_recipe_list(n_clicks, _):
    recipes = pantry.get_all_recipes()
    if not recipes:
        return html.Div("No recipes found")

    recipe_cards = []
    for recipe in recipes:
        ingredients_list = [
            html.Li(f"{ing['quantity']} {ing['unit']} {ing['name']}")
            for ing in recipe["ingredients"]
        ]

        recipe_cards.append(
            dbc.Card(
                [
                    dbc.CardHeader(recipe["name"]),
                    dbc.CardBody(
                        [
                            html.H6("Ingredients:"),
                            html.Ul(ingredients_list),
                            html.H6("Instructions:"),
                            html.P(recipe["instructions"]),
                            html.P(
                                f"Preparation time: {recipe['time_minutes']} minutes"
                            ),
                            html.Small(
                                f"Created: {recipe['created_date']}",
                                className="text-muted",
                            ),
                        ]
                    ),
                ],
                className="mb-3",
            )
        )

    return recipe_cards


# Make Recipe callbacks
# Display all recipes with edit buttons
@app.callback(
    Output("recipe-cards", "children"),
    [Input("refresh-recipes", "n_clicks"), Input("recipe-message", "children")],
)
def display_recipe_cards(_n_clicks, _message):
    recipes = pantry.get_all_recipes()
    if not recipes:
        return html.P("No recipes found")

    cards = []
    for recipe in recipes:
        card = dbc.Card(
            [
                dbc.CardHeader(recipe["name"]),
                dbc.CardBody(
                    [
                        html.H6("Ingredients:"),
                        html.Ul(
                            [
                                html.Li(
                                    f"{ing['quantity']} {ing['unit']} {ing['name']}"
                                )
                                for ing in recipe["ingredients"]
                            ]
                        ),
                        html.H6("Instructions:"),
                        html.P(recipe["instructions"]),
                        html.P(f"Preparation time: {recipe['time_minutes']} minutes"),
                        dbc.Button(
                            "Edit",
                            id={"type": "edit-recipe-button", "recipe": recipe["name"]},
                            color="primary",
                            size="sm",
                        ),
                    ]
                ),
            ],
            className="mb-3",
        )
        cards.append(card)
    return cards


# Combined callback for ingredient lists and edit modal
@app.callback(
    [
        Output("edit-recipe-modal", "is_open"),
        Output("edit-prep-time", "value"),
        Output("edit-instructions", "value"),
        Output("ingredient-list", "children"),
        Output("edit-ingredient-list", "children"),
    ],
    [
        Input({"type": "edit-recipe-button", "recipe": ALL}, "n_clicks"),
        Input("edit-recipe-close", "n_clicks"),
        Input("edit-recipe-save", "n_clicks"),
        Input("add-ingredient-row", "n_clicks"),
        Input("edit-add-ingredient-row", "n_clicks"),
    ],
    [
        State({"type": "edit-recipe-button", "recipe": ALL}, "id"),
        State("ingredient-list", "children"),
        State("edit-ingredient-list", "children"),
    ],
    prevent_initial_call=True,
)
def handle_ingredient_lists_and_edit(
    edit_clicks,
    close_clicks,
    save_clicks,
    new_ing_clicks,
    edit_ing_clicks,
    button_ids,
    new_rows,
    edit_rows,
):
    ctx = callback_context
    if not ctx.triggered:
        return False, None, None, new_rows, edit_rows

    trigger_id = ctx.triggered[0]["prop_id"]

    # Handle edit recipe button clicks
    if ".n_clicks" not in trigger_id:  # It's an edit recipe button
        clicked_idx = next(
            (i for i, clicks in enumerate(edit_clicks) if clicks is not None),
            None,
        )
        if clicked_idx is not None:
            recipe_name = button_ids[clicked_idx]["recipe"]
            recipe = pantry.get_recipe(recipe_name)

            if recipe:
                # Create ingredient rows for edit form
                ingredient_rows = []
                for i, ing in enumerate(recipe["ingredients"]):
                    row = dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Input(
                                        id={"type": "edit-ingredient-name", "index": i},
                                        type="text",
                                        value=ing["name"],
                                        placeholder="Ingredient name",
                                    ),
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Input(
                                        id={
                                            "type": "edit-ingredient-quantity",
                                            "index": i,
                                        },
                                        type="number",
                                        value=ing["quantity"],
                                        placeholder="Quantity",
                                    ),
                                ],
                                width=3,
                            ),
                            dbc.Col(
                                [
                                    dbc.Input(
                                        id={"type": "edit-ingredient-unit", "index": i},
                                        type="text",
                                        value=ing["unit"],
                                        placeholder="Unit",
                                    ),
                                ],
                                width=3,
                            ),
                        ],
                        className="mb-2",
                    )
                    ingredient_rows.append(row)
                return (
                    True,
                    recipe["time_minutes"],
                    recipe["instructions"],
                    new_rows,
                    ingredient_rows,
                )

    # Handle modal close or save
    if trigger_id in ["edit-recipe-close.n_clicks", "edit-recipe-save.n_clicks"]:
        return False, None, None, new_rows, edit_rows

    # Handle add ingredient row clicks
    if trigger_id == "add-ingredient-row.n_clicks":
        if new_ing_clicks is None:
            return False, None, None, new_rows, edit_rows

        new_index = len(new_rows)
        new_row = dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Input(
                            id={"type": "ingredient-name", "index": new_index},
                            type="text",
                            placeholder="Ingredient name",
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        dbc.Input(
                            id={"type": "ingredient-quantity", "index": new_index},
                            type="number",
                            placeholder="Quantity",
                        ),
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Input(
                            id={"type": "ingredient-unit", "index": new_index},
                            type="text",
                            placeholder="Unit",
                        ),
                    ],
                    width=3,
                ),
            ],
            className="mb-2",
        )
        return (
            False,
            None,
            None,
            new_rows + [new_row] if new_rows else [new_row],
            edit_rows,
        )

    if trigger_id == "edit-add-ingredient-row.n_clicks":
        if edit_ing_clicks is None:
            return False, None, None, new_rows, edit_rows

        new_index = len(edit_rows)
        new_row = dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Input(
                            id={"type": "edit-ingredient-name", "index": new_index},
                            type="text",
                            placeholder="Ingredient name",
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        dbc.Input(
                            id={"type": "edit-ingredient-quantity", "index": new_index},
                            type="number",
                            placeholder="Quantity",
                        ),
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Input(
                            id={"type": "edit-ingredient-unit", "index": new_index},
                            type="text",
                            placeholder="Unit",
                        ),
                    ],
                    width=3,
                ),
            ],
            className="mb-2",
        )
        return (
            False,
            None,
            None,
            new_rows,
            edit_rows + [new_row] if edit_rows else [new_row],
        )

    return False, None, None, new_rows, edit_rows


# Handle recipe save (both new and edit)
@app.callback(
    Output("recipe-message", "children"),
    [Input("save-recipe", "n_clicks"), Input("edit-recipe-save", "n_clicks")],
    [
        # States for new recipe
        State("recipe-name", "value"),
        State("prep-time", "value"),
        State("instructions", "value"),
        State({"type": "ingredient-name", "index": ALL}, "value"),
        State({"type": "ingredient-quantity", "index": ALL}, "value"),
        State({"type": "ingredient-unit", "index": ALL}, "value"),
        # States for edit recipe
        State({"type": "edit-recipe-button", "recipe": ALL}, "id"),
        State("edit-prep-time", "value"),
        State("edit-instructions", "value"),
        State({"type": "edit-ingredient-name", "index": ALL}, "value"),
        State({"type": "edit-ingredient-quantity", "index": ALL}, "value"),
        State({"type": "edit-ingredient-unit", "index": ALL}, "value"),
    ],
    prevent_initial_call=True,
)
def save_recipe(
    new_clicks,
    edit_clicks,
    # New recipe states
    recipe_name,
    prep_time,
    instructions,
    ingredient_names,
    ingredient_quantities,
    ingredient_units,
    # Edit recipe states
    button_ids,
    edit_prep_time,
    edit_instructions,
    edit_ingredient_names,
    edit_ingredient_quantities,
    edit_ingredient_units,
):
    ctx = callback_context
    if not ctx.triggered:
        return None

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "save-recipe":
        # Handle new recipe
        if not all([recipe_name, prep_time, instructions]):
            return dbc.Alert("Please fill in all required fields", color="warning")

        ingredients = []
        for name, quantity, unit in zip(
            ingredient_names, ingredient_quantities, ingredient_units
        ):
            if name and quantity and unit:
                ingredients.append(
                    {
                        "name": name,
                        "quantity": float(quantity),
                        "unit": unit,
                    }
                )

        if not ingredients:
            return dbc.Alert("Please add at least one ingredient", color="warning")

        success = pantry.add_recipe(
            name=recipe_name,
            instructions=instructions,
            time_minutes=int(prep_time),
            ingredients=ingredients,
        )

        if success:
            return dbc.Alert("Recipe added successfully", color="success")
        else:
            return dbc.Alert("Failed to add recipe", color="danger")

    elif trigger_id == "edit-recipe-save":
        # Handle edit recipe
        recipe_name = next((bid["recipe"] for bid in button_ids), None)
        if not recipe_name:
            return dbc.Alert("Error: Recipe not found", color="danger")

        if not all([edit_prep_time, edit_instructions]):
            return dbc.Alert("Please fill in all required fields", color="warning")

        ingredients = []
        for name, quantity, unit in zip(
            edit_ingredient_names, edit_ingredient_quantities, edit_ingredient_units
        ):
            if name and quantity and unit:
                ingredients.append(
                    {
                        "name": name,
                        "quantity": float(quantity),
                        "unit": unit,
                    }
                )

        if not ingredients:
            return dbc.Alert("Please add at least one ingredient", color="warning")

        success = pantry.edit_recipe(
            name=recipe_name,
            instructions=edit_instructions,
            time_minutes=int(edit_prep_time),
            ingredients=ingredients,
        )

        if success:
            return dbc.Alert("Recipe updated successfully", color="success")
        else:
            return dbc.Alert("Failed to update recipe", color="danger")

    return None


@app.callback(
    Output("recipe-select", "options"),
    [Input("tabs", "active_tab")],
)
def update_recipe_dropdown(active_tab):
    if active_tab == "make-recipe":
        recipes = pantry.get_all_recipes()
        return [
            {"label": recipe["name"], "value": recipe["name"]} for recipe in recipes
        ]
    return []


@app.callback(
    Output("recipe-details", "children"),
    Input("recipe-select", "value"),
    prevent_initial_call=True,
)
def display_recipe_details(recipe_name):
    if not recipe_name:
        return ""

    recipe = pantry.get_recipe(recipe_name)
    if not recipe:
        return html.Div("Recipe not found", className="text-danger")

    return dbc.Card(
        dbc.CardBody(
            [
                html.H5(recipe["name"], className="card-title"),
                html.P(f"Preparation Time: {recipe['time_minutes']} minutes"),
                html.P("Instructions:"),
                html.Pre(recipe["instructions"]),
            ]
        )
    )


# Preferences page callbacks
@app.callback(
    [
        Output("preferences-table", "data"),
        Output("pref-category", "value"),
        Output("pref-item", "value"),
        Output("pref-level", "value"),
        Output("pref-notes", "value"),
    ],
    [
        Input("add-preference-btn", "n_clicks"),
        Input("preferences-table", "data_previous"),
    ],
    [
        State("pref-category", "value"),
        State("pref-item", "value"),
        State("pref-level", "value"),
        State("pref-notes", "value"),
        State("preferences-table", "data"),
    ],
    prevent_initial_call=True,
)
def manage_preferences(
    n_clicks, previous_data, category, item, level, notes, current_data
):
    """Handle adding and removing preferences."""
    ctx = callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if not current_data:
        current_data = []

    if trigger == "add-preference-btn" and all([category, item, level]):
        # Add new preference
        success = pantry.add_preference(category, item, level, notes)
        if success:
            # Clear input fields and refresh table
            return (
                pantry.get_preferences(),
                None,  # Clear category
                "",  # Clear item
                None,  # Clear level
                "",  # Clear notes
            )
    elif trigger == "preferences-table":
        # Handle row deletion
        if previous_data and len(previous_data) > len(current_data):
            # Find the deleted row
            deleted_row = next(row for row in previous_data if row not in current_data)
            pantry.delete_preference(deleted_row["id"])
        return current_data + [None] * 4  # Keep current table data and clear inputs

    # On first load or if no action taken
    return pantry.get_preferences(), None, "", None, ""


@app.callback(
    Output("make-recipe-message", "children"),
    [
        Input("make-recipe-button", "n_clicks"),
        State("recipe-select", "value"),
        State("scale-factor", "value"),
    ],
    prevent_initial_call=True,
)
def execute_recipe(n_clicks, recipe_name, scale_factor):
    if not recipe_name or not scale_factor:
        return ""

    success, message = pantry.execute_recipe(recipe_name, float(scale_factor))
    # Split message by newlines and create a list of paragraphs
    message_parts = message.split("\n")
    message_components = []
    for i, part in enumerate(message_parts):
        message_components.append(html.P(part))

    return html.Div(
        message_components,
        className=f"text-{'success' if success else 'danger'}",
    )


# Pantry management callbacks
@app.callback(
    [
        Output("add-message", "children"),
        Output("item-name", "value"),
        Output("quantity", "value"),
        Output("unit", "value"),
        Output("notes", "value"),
    ],
    [Input("add-button", "n_clicks")],
    [
        State("item-name", "value"),
        State("quantity", "value"),
        State("unit", "value"),
        State("notes", "value"),
    ],
    prevent_initial_call=True,
)
def add_item(n_clicks, item_name, quantity, unit, notes):
    if not all([item_name, quantity, unit]):
        return (
            dbc.Alert("Please fill in all required fields", color="warning"),
            None,
            None,
            None,
            None,
        )

    try:
        quantity = float(quantity)
        if pantry.add_item(item_name, quantity, unit, notes):
            return (
                dbc.Alert(
                    f"Successfully added {quantity} {unit} of {item_name}",
                    color="success",
                ),
                None,
                None,
                None,
                None,
            )
        else:
            return (
                dbc.Alert("Failed to add item", color="danger"),
                None,
                None,
                None,
                None,
            )
    except ValueError:
        return (
            dbc.Alert("Invalid quantity value", color="danger"),
            None,
            None,
            None,
            None,
        )


@app.callback(
    Output("pantry-contents", "children"),
    [Input("refresh-button", "n_clicks"), Input("add-message", "children")],
)
def update_pantry_contents(_n_clicks, _add_message):
    contents = pantry.get_pantry_contents()
    if not contents:
        return html.P("No items in pantry")

    rows = []
    for item_name, units in contents.items():
        for unit, quantity in units.items():
            rows.append({"Item": item_name, "Quantity": quantity, "Unit": unit})

    return dash_table.DataTable(
        data=rows,
        columns=[{"name": col, "id": col} for col in ["Item", "Quantity", "Unit"]],
        style_cell={"textAlign": "left"},
        style_header={"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold"},
    )


@app.callback(
    Output("transaction-table", "data"),
    [Input("refresh-button", "n_clicks"), Input("add-message", "children")],
)
def update_transaction_history(_n_clicks, _add_message):
    return pantry.get_transaction_history()


if __name__ == "__main__":
    app.run(debug=True)
