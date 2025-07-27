from dash import Dash, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
from pantry_manager import PantryManager

# Initialize the Dash app with Bootstrap theme
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
pantry = PantryManager()

# Layout
app.layout = dbc.Container(
    [
        html.H1("Pantry Manager", className="my-4"),
        # Add Item Form
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
    ],
    fluid=True,
)


# Callbacks
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
    [
        Input("refresh-button", "n_clicks"),
        Input("add-message", "children"),
    ],  # Also refresh when items are added
)
def update_pantry_contents(_n_clicks, _add_message):
    contents = pantry.get_pantry_contents()
    if not contents:
        return html.P("No items in pantry")

    rows = []
    for item_name, units in contents.items():
        for unit, quantity in units.items():
            rows.append(dbc.ListGroupItem(f"{item_name}: {quantity} {unit}"))

    return dbc.ListGroup(rows)


@app.callback(
    Output("transaction-table", "data"),
    [
        Input("refresh-button", "n_clicks"),
        Input("add-message", "children"),
    ],  # Also refresh when items are added
)
def update_transaction_history(_n_clicks, _add_message):
    return pantry.get_transaction_history()


if __name__ == "__main__":
    app.run(debug=True)
