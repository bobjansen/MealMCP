from dash import Dash, html, dcc, Input, Output, State, dash_table, ALL, MATCH
import dash_bootstrap_components as dbc
import json
from pantry_manager import PantryManager

# Initialize the Dash app with Bootstrap theme
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
pantry = PantryManager()


# Layout components
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


def create_recipe_layout():
    return html.Div(
        [
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
                                className="mt-3",
                            ),
                        ]
                    ),
                ]
            ),
        ]
    )


# Main layout with tabs
app.layout = dbc.Container(
    [
        html.H1("Meal & Pantry Manager", className="my-4"),
        dbc.Tabs(
            [
                dbc.Tab(create_pantry_layout(), label="Pantry", tab_id="pantry-tab"),
                dbc.Tab(create_recipe_layout(), label="Recipes", tab_id="recipes-tab"),
            ],
            id="tabs",
            active_tab="pantry-tab",
        ),
    ],
    fluid=True,
    className="p-4",
)


# Callback to add ingredient row
@app.callback(
    Output("ingredient-list", "children"),
    Input("add-ingredient-row", "n_clicks"),
    State("ingredient-list", "children"),
    prevent_initial_call=True,
)
def add_ingredient_row(n_clicks, current_rows):
    if n_clicks is None:
        return current_rows

    new_index = len(current_rows)
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

    return current_rows + [new_row]


# Callback to save recipe
@app.callback(
    Output("recipe-message", "children"),
    Input("save-recipe", "n_clicks"),
    [
        State("recipe-name", "value"),
        State("prep-time", "value"),
        State("instructions", "value"),
        State({"type": "ingredient-name", "index": ALL}, "value"),
        State({"type": "ingredient-quantity", "index": ALL}, "value"),
        State({"type": "ingredient-unit", "index": ALL}, "value"),
    ],
    prevent_initial_call=True,
)
def save_recipe(
    n_clicks, name, time, instructions, ing_names, ing_quantities, ing_units
):
    if None in [name, time, instructions] or not name.strip():
        return html.Div("Please fill in all required fields", className="text-danger")

    ingredients = [
        {"name": name, "quantity": float(qty), "unit": unit}
        for name, qty, unit in zip(ing_names, ing_quantities, ing_units)
        if name and qty and unit
    ]

    if not ingredients:
        return html.Div("Please add at least one ingredient", className="text-danger")

    success = pantry.add_recipe(
        name=name.strip(),
        instructions=instructions.strip(),
        time_minutes=int(time),
        ingredients=ingredients,
    )

    if success:
        return html.Div("Recipe saved successfully!", className="text-success")
    else:
        return html.Div("Error saving recipe", className="text-danger")


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
    # Add Item Form
