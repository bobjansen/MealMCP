"""Whole-row removal uses the current household balance and preserves history."""

from unittest.mock import Mock

import pytest
from bs4 import BeautifulSoup
from werkzeug.routing import Map

import app_flask
from db_setup import setup_database
from db_setup_shared import setup_shared_database
from pantry_manager_shared import SharedPantryManager
from pantry_manager_sqlite import SQLitePantryManager


@pytest.fixture(params=["local", "shared"])
def pantry_client(tmp_path, monkeypatch, request):
    db_path = str(tmp_path / "pantry.db")
    if request.param == "shared":
        assert setup_shared_database(db_path)
        pantry = SharedPantryManager(db_path, user_id=7, backend="sqlite")
    else:
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
    forms = page.select('form[action="/pantry/remove"]')
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
    response = client.post("/pantry/remove", data=fields)
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
    client.post("/pantry/remove", data=fields)
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
            "/pantry/remove", data={"csrf_token": token, "remove_all": "1", **fields}
        )
        assert response.status_code == 302
    assert pantry.get_item_quantity("Milk", "Liter") == 1.5
    assert len(pantry.get_transaction_history()) == 2


def test_remove_button_requires_csrf_and_login(pantry_client, monkeypatch):
    pantry, client = pantry_client
    form = remove_form(client)
    fields = {field["name"]: field["value"] for field in form.select("input")}
    client.post("/pantry/remove", data={"item_name": "Milk", "unit": "Liter"})
    assert pantry.get_item_quantity("Milk", "Liter") == 1.5

    with client.session_transaction() as session:
        session.pop("user_id")
    getter = Mock(return_value=pantry)
    monkeypatch.setattr(app_flask, "get_current_user_pantry", getter)
    response = client.post("/pantry/remove", data=fields)
    assert response.headers["Location"].endswith("/login")
    getter.assert_not_called()
    assert pantry.get_item_quantity("Milk", "Liter") == 1.5


def test_pantry_renders_without_extra_removal_endpoint(pantry_client, monkeypatch):
    _, client = pantry_client
    # Reproduce the production route map from the reported BuildError.
    rules = [
        rule.empty()
        for rule in app_flask.app.url_map.iter_rules()
        if rule.endpoint != "remove_all_pantry_item"
    ]
    monkeypatch.setattr(app_flask.app, "url_map", Map(rules))
    response = client.get("/pantry")
    assert response.status_code == 200
    page = BeautifulSoup(response.get_data(as_text=True), "html.parser")
    assert page.select('form[action="/pantry/remove"] input[name="remove_all"]')


def test_existing_partial_removal_still_works(pantry_client):
    pantry, client = pantry_client
    token = remove_form(client).select_one('[name="csrf_token"]')["value"]
    response = client.post(
        "/pantry/remove",
        data={
            "csrf_token": token,
            "item_name": "Milk",
            "unit": "Liter",
            "quantity": "0.5",
        },
    )
    assert response.status_code == 302
    assert pantry.get_item_quantity("Milk", "Liter") == 1


def test_shared_removal_preserves_other_households_stock(tmp_path, monkeypatch, caplog):
    db_path = str(tmp_path / "shared.db")
    assert setup_shared_database(db_path)
    owner = SharedPantryManager(db_path, user_id=1, backend="sqlite")
    other = SharedPantryManager(db_path, user_id=2, backend="sqlite")
    assert owner.add_item("Spinazie", 250, "Gram")
    assert other.add_item("Spinazie", 750, "Gram")
    monkeypatch.setattr(app_flask, "get_current_user_pantry", lambda: owner)
    monkeypatch.setattr(app_flask.auth_ctx, "backend", "sqlite")
    monkeypatch.setitem(app_flask.app.config, "TESTING", True)
    monkeypatch.setitem(app_flask.app.config, "WTF_CSRF_ENABLED", False)
    with caplog.at_level("INFO", logger="app_flask"):
        response = app_flask.app.test_client().post(
            "/pantry/remove",
            data={"remove_all": "1", "item_name": "Spinazie", "unit": "Gram"},
        )
    assert response.status_code == 302
    assert "Spinazie" not in owner.get_pantry_contents()
    assert other.get_item_quantity("Spinazie", "Gram") == 750
    assert "Removed all 250.0 Gram of 'Spinazie' from pantry" in caplog.text
