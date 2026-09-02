from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path

target = Path(os.environ["TARGET_REPO"])
module_spec = importlib.util.spec_from_file_location(
    "holdout_inventory", target / "src" / "inventory.py"
)
assert module_spec and module_spec.loader
inventory = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(inventory)
add_item = inventory.add_item


class StrictQuantityAcceptance(unittest.TestCase):
    def test_booleans_are_rejected_but_positive_integers_still_work(self):
        for value in (True, False):
            with self.subTest(value=value), self.assertRaises(ValueError):
                add_item([], "Washers", value)

        self.assertEqual(
            add_item([], "Washers", 2),
            [{"name": "Washers", "quantity": 2}],
        )


if __name__ == "__main__":
    unittest.main()
