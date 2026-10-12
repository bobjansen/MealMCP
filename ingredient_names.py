"""Shared ingredient matching rules without guessing synonyms or misspellings."""

import unicodedata


def ingredient_key(name: str) -> str:
    """Ignore case and whitespace, including spaces inside compound names."""
    return "".join(unicodedata.normalize("NFKC", name).casefold().split())


def matching_ingredient_ids(manager, name: str):
    """Find all historical spelling variants, scoped to the current household."""
    key = ingredient_key(name)
    if not key:
        return []
    with manager._get_connection() as conn:
        cursor = conn.cursor()
        try:
            if hasattr(manager, "user_id"):
                ph = manager._get_placeholder()
                cursor.execute(
                    f"SELECT id, name FROM ingredients "
                    f"WHERE user_id = {ph} ORDER BY id",
                    (manager.user_id,),
                )
            else:
                cursor.execute("SELECT id, name FROM Ingredients ORDER BY id")
            return [
                ingredient_id
                for ingredient_id, stored_name in cursor.fetchall()
                if ingredient_key(stored_name) == key
            ]
        finally:
            cursor.close()


def combine_ingredient_rows(rows):
    """Combine (name, unit, quantity) rows, preserving the first display spelling."""
    names = {}
    contents = {}
    for name, unit, quantity in rows:
        key = ingredient_key(name)
        display_name = names.setdefault(key, name)
        units = contents.setdefault(display_name, {})
        units[unit] = units.get(unit, 0.0) + float(quantity or 0)
    return {
        name: {unit: qty for unit, qty in units.items() if qty > 0}
        for name, units in contents.items()
        if any(qty > 0 for qty in units.values())
    }


def combine_requirements(required):
    contents = combine_ingredient_rows(
        (name, unit, quantity) for (name, unit), quantity in required.items()
    )
    return {
        (name, unit): quantity
        for name, units in contents.items()
        for unit, quantity in units.items()
    }


def combine_recipe_ingredients(ingredients):
    """Coalesce repeated spellings within a recipe before inserting its rows."""
    combined = {}
    for item in ingredients:
        key = (ingredient_key(item["name"]), item["unit"])
        if key not in combined:
            combined[key] = dict(item)
        else:
            combined[key]["quantity"] += item["quantity"]
    return list(combined.values())
