import unittest

from src.inventory import add_item


class AddItemTests(unittest.TestCase):
    def test_adds_trimmed_item_without_mutating_input(self):
        original = [{"name": "Bolts", "quantity": 4}]

        updated = add_item(original, "  Washers  ", 2)

        self.assertEqual(original, [{"name": "Bolts", "quantity": 4}])
        self.assertEqual(updated[-1], {"name": "Washers", "quantity": 2})

    def test_rejects_blank_name_and_non_positive_quantity(self):
        with self.assertRaises(ValueError):
            add_item([], "   ", 1)
        with self.assertRaises(ValueError):
            add_item([], "Washers", 0)


if __name__ == "__main__":
    unittest.main()
