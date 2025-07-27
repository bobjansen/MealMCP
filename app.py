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
from constants import UNITS
from pantry_manager import PantryManager
from i18n import t


def format_recipe_markdown(recipe):
    """Format a recipe as markdown text."""
    ingredients_list = "\n".join(
        f"- {ing['quantity']} {ing['unit']} {ing['name']}"
        for ing in recipe["ingredients"]
    )

    return f"""# {recipe['name']}

## Preparation Time
{recipe['time_minutes']} minutes

## Ingredients
{ingredients_list}

## Instructions
{recipe['instructions']}

---
*Created: {recipe['created_date']}*
*Last Modified: {recipe['last_modified']}*
"""


# Initialize the Dash app with Bootstrap theme
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
pantry = PantryManager()


# Layout components
def create_preferences_layout():
    return html.Div(
        [
            dbc.Card(
                [
                    dbc.CardHeader(t("Food Preferences")),
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
                                                                        t("Category")
                                                                    ),
                                                                    dcc.Dropdown(
                                                                        id="pref-category",
                                                                        options=[
                                                                            {
                                                                                "label": t("Dietary Restriction"),
                                                                                "value": "dietary",
                                                                            },
                                                                            {
                                                                                "label": t("Allergy"),
                                                                                "value": "allergy",
                                                                            },
                                                                            {
                                                                                "label": t("Dislike"),
                                                                                "value": "dislike",
                                                                            },
                                                                        ],
                                                                        placeholder=t("Select category"),
                                                                    ),
                                                                ],
                                                                width=3,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Label(t("Item")),
                                                                    dbc.Input(
                                                                        id="pref-item",
                                                                        type="text",
                                                                        placeholder=t("Enter item (e.g., vegetarian, peanuts)"),
                                                                    ),
                                                                ],
                                                                width=3,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Label(t("Level")),
                                                                    dcc.Dropdown(
                                                                        id="pref-level",
                                                                        options=[
                                                                            {
                                                                                "label": t("Required"),
                                                                                "value": "required",
                                                                            },
                                                                            {
                                                                                "label": t("Preferred"),
                                                                                "value": "preferred",
                                                                            },
                                                                            {
                                                                                "label": t("Avoid"),
                                                                                "value": "avoid",
                                                                            },
                                                                        ],
                                                                        placeholder=t("Select level"),
                                                                    ),
                                                                ],
                                                                width=3,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Label(t("Notes")),
                                                                    dbc.Input(
                                                                        id="pref-notes",
                                                                        type="text",
                                                                        placeholder=t("Optional notes"),
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
                                                                t("Add Preference"),
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
                                            html.H4(t("Current Preferences")),
                                            dash_table.DataTable(
                                                id="preferences-table",
                                                columns=[
                                                    {
                                                        "name": t("Category"),
                                                        "id": "category",
                                                    },
                                                    {"name": t("Item"), "id": "item"},
                                                    {"name": t("Level"), "id": "level"},
                                                    {"name": t("Notes"), "id": "notes"},
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
                    dbc.CardHeader(t("Make Recipe")),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(t("Select Recipe")),
                                            dcc.Dropdown(
                                                id="recipe-select",
                                                options=[],
                                                placeholder=t("Choose a recipe"),
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Br(),
                                            dbc.Button(
                                                t("Make Recipe"),
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
            # Recipe Details Modal for viewing and making
            dbc.Modal(
                [
                    dbc.ModalHeader(html.H4(id="recipe-modal-title")),
                    dbc.ModalBody(
                        [
                            html.Div(id="recipe-modal-content"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                t("Make Recipe"),
                                                id="make-recipe-button",
                                                color="success",
                                                className="mt-4",
                                            ),
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                t("Edit Recipe"),
                                                id="edit-recipe-button",
                                                color="primary",
                                                className="mt-4",
                                            ),
                                        ],
                                        width=4,
                                    ),
                                ],
                                className="mt-3",
                            ),
                            html.Div(id="make-recipe-message", className="mt-3"),
                        ]
                    ),
                    dbc.ModalFooter(
                        dbc.Button(
                            t("Close"), id="recipe-modal-close", className="ms-auto"
                        )
                    ),
                ],
                id="recipe-view-modal",
                size="lg",
            ),
            # Edit Recipe Modal
            dbc.Modal(
                [
                    dbc.ModalHeader(t("Edit Recipe")),
                    dbc.ModalBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(t("Preparation Time (minutes)")),
                                            dbc.Input(
                                                id="edit-prep-time",
                                                type="number",
                                                placeholder=t("Enter preparation time"),
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
                                            dbc.Label(t("Instructions")),
                                            dbc.Textarea(
                                                id="edit-instructions",
                                                placeholder=t("Enter cooking instructions"),
                                                style={"height": "150px"},
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Div(
                                [
                                    html.H5(t("Ingredients"), className="mb-3"),
                                    html.Div(
                                        id="edit-ingredient-list",
                                        children=[],
                                    ),
                                    dbc.Button(
                                        t("Add Ingredient"),
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
                                t("Cancel"), id="edit-recipe-close", className="me-2"
                            ),
                            dbc.Button(
                                t("Save Changes"),
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
                    dbc.CardHeader(t("Add New Recipe")),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(t("Recipe Name")),
                                            dbc.Input(
                                                id="recipe-name",
                                                type="text",
                                                placeholder=t("Enter recipe name"),
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(t("Preparation Time (minutes)")),
                                            dbc.Input(
                                                id="prep-time",
                                                type="number",
                                                placeholder=t("Enter preparation time"),
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
                                            dbc.Label(t("Instructions")),
                                            dbc.Textarea(
                                                id="instructions",
                                                placeholder=t("Enter cooking instructions"),
                                                style={"height": "150px"},
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Div(
                                [
                                    html.H5(t("Ingredients"), className="mb-3"),
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
                                                                placeholder=t("Ingredient name"),
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
                                                                placeholder=t("Quantity"),
                                                            ),
                                                        ],
                                                        width=3,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dcc.Dropdown(
                                                                UNITS,
                                                                UNITS[-1],
                                                                id="ingredient-unit",
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
                                        t("Add Ingredient"),
                                        id="add-ingredient-row",
                                        color="secondary",
                                        size="sm",
                                        className="mt-2",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Button(
                                t("Save Recipe"), id="save-recipe", color="primary"
                            ),
                            html.Div(id="recipe-message", className="mt-3"),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            dbc.Card(
                [
                    dbc.CardHeader(t("Recipe Management")),
                    dbc.CardBody(
                        [
                            dash_table.DataTable(
                                id="recipes-table",
                                columns=[
                                    {"name": t("Recipe Name"), "id": "name"},
                                    {"name": t("Prep Time"), "id": "time_minutes"},
                                    {
                                        "name": t("Actions"),
                                        "id": "actions",
                                        "presentation": "markdown",
                                    },
                                ],
                                data=[],
                                style_data={
                                    "whiteSpace": "normal",
                                    "height": "auto",
                                },
                                style_cell={
                                    "textAlign": "left",
                                    "padding": "10px",
                                },
                                style_header={
                                    "backgroundColor": "rgb(230, 230, 230)",
                                    "fontWeight": "bold",
                                },
                                markdown_options={"html": True},
                            ),
                            dbc.Button(
                                t("Refresh Recipes"),
                                id="refresh-recipes",
                                color="secondary",
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
                    dbc.CardHeader(t("Add Item to Pantry")),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(t("Item Name")),
                                            dbc.Input(
                                                id="item-name",
                                                type="text",
                                                placeholder=t("Enter item name"),
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(t("Quantity")),
                                            dbc.Input(
                                                id="quantity",
                                                type="number",
                                                placeholder=t("Enter quantity"),
                                            ),
                                        ],
                                        width=2,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(t("Unit")),
                                            dbc.Input(
                                                id="unit",
                                                type="text",
                                                placeholder=t("e.g., g, kg, ml"),
                                            ),
                                        ],
                                        width=2,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(t("Notes")),
                                            dbc.Input(
                                                id="notes",
                                                type="text",
                                                placeholder=t("Optional notes"),
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Br(),
                                            dbc.Button(
                                                t("Add Item"),
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
                    dbc.CardHeader(t("Current Pantry Contents")),
                    dbc.CardBody(
                        [
                            html.Div(id="pantry-contents"),
                            dbc.Button(
                                t("Refresh"),
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
                    dbc.CardHeader(t("Transaction History")),
                    dbc.CardBody(
                        [
                            dash_table.DataTable(
                                id="transaction-table",
                                columns=[
                                    {"name": t("Date"), "id": "transaction_date"},
                                    {"name": t("Type"), "id": "transaction_type"},
                                    {"name": t("Item"), "id": "item_name"},
                                    {"name": t("Quantity"), "id": "quantity"},
                                    {"name": t("Unit"), "id": "unit"},
                                    {"name": t("Notes"), "id": "notes"},
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
        html.H1(t("Meal Planner"), className="my-4"),
        dbc.Tabs(
            [
                dbc.Tab(
                    create_pantry_layout(), label=t("Pantry Management"), tab_id="pantry"
                ),
                dbc.Tab(create_recipe_layout(), label=t("Recipes"), tab_id="recipes"),
                dbc.Tab(
                    create_preferences_layout(),
                    label=t("Preferences"),
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
    Output("recipes-table", "data"),
    [Input("refresh-recipes", "n_clicks"), Input("recipe-message", "children")],
)
def update_recipe_list(n_clicks, _):
    recipes = pantry.get_all_recipes()
    if not recipes:
        return []

    table_data = []
    for recipe in recipes:
        table_data.append(
            {
                "name": recipe["name"],
                "time_minutes": f"{recipe['time_minutes']} mins",
                "actions": f"<button id='view-{recipe['name']}' class='btn btn-primary btn-sm'>View</button>",
            }
        )

    return table_data


# Recipe edit and ingredient management callbacks


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
                                        placeholder=t("Ingredient name"),
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
                                        placeholder=t("Quantity"),
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
                                        placeholder=t("Unit"),
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
                            placeholder=t("Ingredient name"),
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        dbc.Input(
                            id={"type": "ingredient-quantity", "index": new_index},
                            type="number",
                            placeholder=t("Quantity"),
                        ),
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Input(
                            id={"type": "ingredient-unit", "index": new_index},
                            type="text",
                            placeholder=t("Unit"),
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
                            placeholder=t("Ingredient name"),
                        ),
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        dbc.Input(
                            id={"type": "edit-ingredient-quantity", "index": new_index},
                            type="number",
                            placeholder=t("Quantity"),
                        ),
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Input(
                            id={"type": "edit-ingredient-unit", "index": new_index},
                            type="text",
                            placeholder=t("Unit"),
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
        return ""

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "save-recipe":
        if not recipe_name or not prep_time or not instructions:
            return "Please fill in all required fields"

        ingredients = []
        for name, qty, unit in zip(
            ingredient_names, ingredient_quantities, ingredient_units
        ):
            if name and qty and unit:
                ingredients.append({"name": name, "quantity": float(qty), "unit": unit})

        try:
            pantry.add_recipe(recipe_name, int(prep_time), instructions, ingredients)
            return "Recipe saved successfully!"
        except Exception as e:
            return f"Error saving recipe: {str(e)}"

    elif trigger_id == "edit-recipe-save":
        if not edit_prep_time or not edit_instructions:
            return "Please fill in all required fields"

        ingredients = []
        for name, qty, unit in zip(
            edit_ingredient_names, edit_ingredient_quantities, edit_ingredient_units
        ):
            if name and qty and unit:
                ingredients.append({"name": name, "quantity": float(qty), "unit": unit})

        clicked_idx = next(
            (i for i, clicks in enumerate(edit_clicks) if clicks is not None), None
        )
        if clicked_idx is not None:
            recipe_name = button_ids[clicked_idx]["recipe"]
            try:
                pantry.update_recipe(
                    recipe_name, int(edit_prep_time), edit_instructions, ingredients
                )
                return "Recipe updated successfully!"
            except Exception as e:
                return f"Error updating recipe: {str(e)}"

    return ""


# Callback for recipe view modal
@app.callback(
    [
        Output("recipe-view-modal", "is_open"),
        Output("recipe-modal-title", "children"),
        Output("recipe-modal-content", "children"),
    ],
    [Input("recipes-table", "active_cell"), Input("recipe-modal-close", "n_clicks")],
    [State("recipes-table", "data")],
)
def toggle_recipe_modal(active_cell, close_clicks, table_data):
    ctx = callback_context
    if not ctx.triggered:
        return False, "", None

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "recipe-modal-close":
        return False, "", None

    if active_cell is not None:
        recipe_name = table_data[active_cell["row"]]["name"]
        recipe = pantry.get_recipe(recipe_name)
        if recipe:
            return True, recipe["name"], dcc.Markdown(format_recipe_markdown(recipe))

    return False, "", None


# Callback for recipe actions (making, closing modal)
@app.callback(
    Output("make-recipe-message", "children"),
    [
        Input("make-recipe-button", "n_clicks"),
        Input("recipe-modal-close", "n_clicks"),
        Input("edit-recipe-button", "n_clicks"),
    ],
    [
        State("recipe-modal-title", "children"),
    ],
    prevent_initial_call=True,
)
def handle_recipe_actions(make_clicks, close_clicks, edit_clicks, recipe_name):
    ctx = callback_context
    if not ctx.triggered:
        return None

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "recipe-modal-close":
        return None

    if trigger_id == "make-recipe-button" and make_clicks:
        try:
            result = pantry.make_recipe(recipe_name)
            return dbc.Alert(f"Successfully made recipe: {result}", color="success")
        except Exception as e:
            return dbc.Alert(f"Error making recipe: {str(e)}", color="danger")

    return None


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
        Input("tabs", "active_tab"),
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
    n_clicks, previous_data, active_tab, category, item, level, notes, current_data
):
    """Handle adding and removing preferences."""
    ctx = callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if not current_data:
        current_data = []

    if trigger == "tabs" and active_tab == "preferences":
        return pantry.get_preferences(), None, "", None, ""

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


# Recipe execution is now handled in the handle_recipe_actions callback


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
