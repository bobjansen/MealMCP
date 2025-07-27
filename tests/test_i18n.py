import unittest
import sys
from pathlib import Path

# Add repo root to path
sys.path.append(str(Path(__file__).parent.parent))

from i18n import translator

class TestTranslator(unittest.TestCase):
    def test_translation(self):
        translator.set_language("nl")
        self.assertEqual(translator.translate("Meal Planner"), "Maaltijdplanner")
        self.assertEqual(translator.translate("Unknown"), "Unknown")
        translator.set_language("en")
        self.assertEqual(translator.translate("Meal Planner"), "Meal Planner")

if __name__ == "__main__":
    unittest.main()
