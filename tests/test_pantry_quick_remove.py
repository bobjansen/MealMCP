"""Whole-row removal uses the current household balance and preserves history."""

from unittest.mock import Mock

import pytest
from bs4 import BeautifulSoup

import app_flask
from db_setup import setup_database
from pantry_manager_sqlite import SQLitePantryManager


@pytest.fixture
def pantry_client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "pantry.db")
    setup_database(db_path)
    pantry = SQLitePantryManager(db_path)
    assert pantry.add_item("Milk", 1.5, "Liter")
    assert pantry.add_item("Flour", 500, "Gram")
    monkeypatch.setattr(app_flask, "get_current_user_pantry", lambda: pantry)
    monkeypatch.setattr(app_flask.auth_ctx, "backend", "postgresql")
    monkeypatch.setattr(
        app_flask.auth_ctx.auth_manager, "get_user_by_id", lambda uid: {"id": uid}
    )
    monkeypatch.setattr(app_flask.i18n, "LANG", "en")
    monkeypatch.setitem(app_flask.app.config, "TESTING", True)
    monkeypatch.setitem(app_flask.app.config, "WTF_CSRF_ENABLED", True)
    client = app_flask.app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 7
    return pantry, client


def remove_form(client):
    page = BeautifulSoup(client.get("/pantry").get_data(as_text=True), "html.parser")
    forms = page.select('form[action="/pantry/remove-all"]')
    return next(
        form
        for form in forms
        if form.select_one('[name="item_name"]')["value"] == "Milk"
    )


def test_button_removes_current_balance_without_entering_quantity(pantry_client):
    pantry, client = pantry_client
    form = remove_form(client)
    assert form.select_one('button[type="submit"]') is not None
    assert form.select_one('[name="quantity"]') is None
    fields = {field["name"]: field["value"] for field in form.select("input")}
    # The browser's old balance must not leave newly added stock behind.
    assert pantry.add_item("Milk", 0.5, "Liter")
    response = client.post("/pantry/remove-all", data=fields)
    assert response.status_code == 302
    assert "Milk" not in pantry.get_pantry_contents()
    assert pantry.get_item_quantity("Flour", "Gram") == 500
    removals = [
        row
        for row in pantry.get_transaction_history()
        if row["transaction_type"] == "removal"
    ]
    assert len(removals) == 1
    assert removals[0]["quantity"] == 2
    # Retrying the same submission must not create negative inventory.
    client.post("/pantry/remove-all", data=fields)
    assert pantry.get_item_quantity("Milk", "Liter") == 0
    assert len(pantry.get_transaction_history()) == 4


def test_unknown_item_or_unit_does_not_remove_stock(pantry_client):
    pantry, client = pantry_client
    token = remove_form(client).select_one('[name="csrf_token"]')["value"]
    for fields in (
        {},
        {"item_name": "Milk", "unit": "Gram"},
        {"item_name": "Unknown", "unit": "Liter"},
    ):
        response = client.post(
            "/pantry/remove-all", data={"csrf_token": token, **fields}
        )
        assert response.status_code == 302
    assert pantry.get_item_quantity("Milk", "Liter") == 1.5
    assert len(pantry.get_transaction_history()) == 2


def test_remove_button_requires_csrf_and_login(pantry_client, monkeypatch):
    pantry, client = pantry_client
    form = remove_form(client)
    fields = {field["name"]: field["value"] for field in form.select("input")}
    client.post("/pantry/remove-all", data={"item_name": "Milk", "unit": "Liter"})
    assert pantry.get_item_quantity("Milk", "Liter") == 1.5
    with client.session_transaction() as session:
        session.pop("user_id")
    getter = Mock(return_value=pantry)
    monkeypatch.setattr(app_flask, "get_current_user_pantry", getter)
    response = client.post("/pantry/remove-all", data=fields)
    assert response.headers["Location"].endswith("/login")
    getter.assert_not_called()
    assert pantry.get_item_quantity("Milk", "Liter") == 1.5
