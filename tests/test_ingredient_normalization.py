"""Ingredient spelling variants share balances, recipes, and grocery needs."""

from datetime import date, timedelta

import pytest

import app_flask
from db_setup import setup_database
from db_setup_shared import setup_shared_database
from ingredient_names import ingredient_key
from pantry_manager_shared import SharedPantryManager
from pantry_manager_sqlite import SQLitePantryManager


@pytest.fixture(params=["local", "shared"])
def pantry(request, tmp_path, monkeypatch):
    monkeypatch.setattr(app_flask.i18n, "LANG", "en")
    path = str(tmp_path / "pantry.db")
    if request.param == "shared":
        assert setup_shared_database(path)
        return SharedPantryManager(path, user_id=1, backend="sqlite")
    setup_database(path)
    return SQLitePantryManager(path)


def seed_legacy_variants(pantry):
    """Simulate names already saved separately before normalization existed."""
    with pantry._get_connection() as conn:
        cursor = conn.cursor()
        ids = []
        for name, quantity in [("olijf olie", 40), ("Olijfolie", 60)]:
            if isinstance(pantry, SharedPantryManager):
                cursor.execute(
                    "INSERT INTO ingredients (user_id, name, default_unit) "
                    "VALUES (1, ?, 'Milliliter')",
                    (name,),
                )
                ingredient_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO pantry_transactions "
                    "(user_id, ingredient_id, unit, quantity, "
                    "transaction_type, transaction_date) "
                    "VALUES (1, ?, 'Milliliter', ?, 'addition', '2026-10-12')",
                    (ingredient_id, quantity),
                )
            else:
                cursor.execute(
                    "INSERT INTO Ingredients (name, default_unit) "
                    "VALUES (?, 'Milliliter')",
                    (name,),
                )
                ingredient_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO PantryTransactions "
                    "(ingredient_id, unit, quantity, "
                    "transaction_type, transaction_date) "
                    "VALUES (?, 'Milliliter', ?, 'addition', '2026-10-12')",
                    (ingredient_id, quantity),
                )
            ids.append(ingredient_id)
        return ids


def test_new_variants_reuse_the_same_ingredient(pantry):
    assert pantry.add_item("olijf olie", 20, "Milliliter")
    assert pantry.add_item("Olijfolie", 30, "Milliliter")
    assert pantry.add_item("  OLIJF   OLIE  ", 50, "Milliliter")
    assert pantry.get_ingredient_id("Olijfolie") == pantry.get_ingredient_id(
        "olijf olie"
    )
    assert pantry.get_item_quantity("OLIJFOLIE", "Milliliter") == 100
    assert len(pantry.get_pantry_contents()) == 1
    assert pantry.remove_item("olijf\tolie", 25, "Milliliter")
    assert pantry.get_item_quantity("Olijfolie", "Milliliter") == 75
    with pantry._get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0] == 1


def test_existing_variants_combine_without_losing_history(pantry):
    original_ids = seed_legacy_variants(pantry)
    assert pantry.get_item_quantity("Olijfolie", "Milliliter") == 100
    assert pantry.get_total_item_quantity("OLIJF OLIE", "Liter") == pytest.approx(0.1)
    assert len(pantry.get_pantry_contents()) == 1
    assert pantry.remove_item("Olijfolie", 100, "Milliliter")
    assert pantry.get_pantry_contents() == {}
    assert pantry.get_item_quantity("olijf olie", "Milliliter") == 0
    assert len(pantry.get_transaction_history()) == 3
    assert pantry.add_item("OLIJFOLIE", 25, "Milliliter")
    assert pantry.get_item_quantity("Olijfolie", "Milliliter") == 25
    assert list(pantry.get_pantry_contents().values()) == [{"Milliliter": 25}]
    with pantry._get_connection() as conn:
        assert [
            row[0] for row in conn.execute("SELECT id FROM ingredients ORDER BY id")
        ] == original_ids


def test_recipe_spelling_uses_pantry_stock(pantry):
    assert pantry.add_item("olijf olie", 100, "Milliliter")
    assert pantry.add_recipe(
        "Salade",
        "Mix",
        10,
        [
            {"name": "Olijfolie", "quantity": 120, "unit": "Milliliter"},
        ],
    )
    assert pantry.set_meal_plan(date.today().isoformat(), "Salade")
    grocery = pantry.get_grocery_list()
    assert len(grocery) == 1
    assert ingredient_key(grocery[0]["name"]) == "olijfolie"
    assert grocery[0]["quantity"] == 20


def test_legacy_recipe_requirements_combine_before_subtracting_stock(pantry):
    _, second_id = seed_legacy_variants(pantry)
    for offset, recipe_name in enumerate(["Salade", "Pasta"]):
        assert pantry.add_recipe(
            recipe_name,
            "Mix",
            10,
            [
                {"name": "Olijfolie", "quantity": 60, "unit": "Milliliter"},
            ],
        )
        assert pantry.set_meal_plan(
            (date.today() + timedelta(days=offset)).isoformat(), recipe_name
        )
    # Make the second historical recipe reference the old separate spelling.
    table = (
        "recipe_ingredients"
        if isinstance(pantry, SharedPantryManager)
        else "RecipeIngredients"
    )
    with pantry._get_connection() as conn:
        conn.execute(
            f"UPDATE {table} SET ingredient_id = ? "
            "WHERE recipe_id = (SELECT id FROM recipes WHERE name = 'Pasta')",
            (second_id,),
        )
    grocery = pantry.get_grocery_list()
    assert len(grocery) == 1
    assert grocery[0]["quantity"] == 20


def test_duplicate_spellings_within_a_recipe_combine(pantry):
    ingredients = [
        {"name": "olijf olie", "quantity": 10, "unit": "Milliliter"},
        {"name": "Olijfolie", "quantity": 20, "unit": "Milliliter"},
    ]
    assert pantry.add_recipe("Salade", "Mix", 10, ingredients)
    recipe = pantry.get_recipe("Salade")
    assert len(recipe["ingredients"]) == 1
    assert recipe["ingredients"][0]["quantity"] == 30
    assert ingredients[0]["quantity"] == 10


def test_quick_remove_works_with_an_old_spelling(pantry, monkeypatch):
    seed_legacy_variants(pantry)
    monkeypatch.setattr(app_flask, "get_current_user_pantry", lambda: pantry)
    monkeypatch.setattr(app_flask.auth_ctx, "backend", "sqlite")
    monkeypatch.setitem(app_flask.app.config, "WTF_CSRF_ENABLED", False)
    response = app_flask.app.test_client().post(
        "/pantry/remove",
        data={"item_name": "OLIJF OLIE", "unit": "Milliliter", "remove_all": "1"},
    )
    assert response.status_code == 302
    assert pantry.get_pantry_contents() == {}


def test_similar_ingredients_and_households_remain_separate(pantry):
    assert pantry.add_item("Olijfolie", 50, "Milliliter")
    assert pantry.add_item("Zonnebloemolie", 70, "Milliliter")
    assert len(pantry.get_pantry_contents()) == 2
    assert pantry.get_item_quantity("Olijf olie", "Milliliter") == 50
    if isinstance(pantry, SharedPantryManager):
        other = SharedPantryManager(
            pantry.connection_string, user_id=2, backend="sqlite"
        )
        assert other.add_item("olijf olie", 1000, "Milliliter")
        assert other.get_item_quantity("Olijfolie", "Milliliter") == 1000
        assert pantry.get_item_quantity("Olijfolie", "Milliliter") == 50


def test_unicode_and_whitespace_keys():
    assert ingredient_key("Olijf\u00a0olie") == ingredient_key("OLIJFOLIE")
    assert ingredient_key("Cafe\u0301") == ingredient_key("Café")
    assert ingredient_key("olive oil") != ingredient_key("olive-oil")
    assert ingredient_key("salt") != ingredient_key("salted butter")
