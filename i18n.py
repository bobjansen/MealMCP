class Translator:
    def __init__(self, language="en"):
        self.language = language
        self.translations = {
            "en": {},
            "nl": {
                "Meal Planner": "Maaltijdplanner",
                "Pantry Management": "Voorraadbeheer",
                "Recipes": "Recepten",
                "Preferences": "Voorkeuren",
                "Add Item": "Voeg item toe",
                "Add Item to Pantry": "Item aan voorraad toevoegen",
                "Item Name": "Itemnaam",
                "Quantity": "Hoeveelheid",
                "Unit": "Eenheid",
                "Notes": "Notities",
                "Current Pantry Contents": "Huidige voorraad",
                "Refresh": "Vernieuwen",
                "Transaction History": "Transactiegeschiedenis",
                "Add Preference": "Voeg voorkeur toe",
                "Food Preferences": "Voedselvoorkeuren",
                "Category": "Categorie",
                "Item": "Item",
                "Level": "Niveau",
                "Current Preferences": "Huidige voorkeuren",
                "Make Recipe": "Maak recept",
                "Edit Recipe": "Bewerk recept",
                "Add New Recipe": "Nieuw recept toevoegen",
                "Recipe Name": "Naam recept",
                "Preparation Time (minutes)": "Bereidingstijd (minuten)",
                "Instructions": "Instructies",
                "Ingredients": "Ingrediënten",
                "Select Recipe": "Selecteer recept",
                "Recipe Details": "Receptdetails",
                "Edit": "Bewerk",
                "Delete": "Verwijder",
                "View": "Bekijk",
                "Invalid quantity value": "Ongeldige hoeveelheid",
                "Failed to add item": "Toevoegen mislukt",
                "Successfully added {quantity} {unit} of {item_name}": "Succesvol {quantity} {unit} {item_name} toegevoegd",
                "No items in pantry": "Geen items in voorraad",
                "Please fill in all required fields": "Vul alle verplichte velden in",
                "Recipe saved successfully!": "Recept succesvol opgeslagen!",
                "Recipe updated successfully!": "Recept succesvol bijgewerkt!",
                "Successfully made recipe: {result}": "Recept succesvol gemaakt: {result}",
                "Error making recipe: {error}": "Fout bij het maken van recept: {error}",
            },
        }

    def set_language(self, language: str):
        self.language = language

    def translate(self, text: str) -> str:
        return self.translations.get(self.language, {}).get(text, text)

translator = Translator()

def translate_component(component):
    """Recursively translate strings in a Dash component tree."""
    from collections.abc import Iterable

    if isinstance(component, str):
        return translator.translate(component)

    # Handle iterable components like lists or tuples
    if isinstance(component, Iterable) and not hasattr(component, "children"):
        return [translate_component(c) for c in component]

    # Translate common text properties
    for attr in ["children", "label", "placeholder", "title"]:
        if hasattr(component, attr):
            value = getattr(component, attr)
            if isinstance(value, str):
                setattr(component, attr, translator.translate(value))
            elif isinstance(value, Iterable):
                setattr(component, attr, translate_component(value))

    return component
