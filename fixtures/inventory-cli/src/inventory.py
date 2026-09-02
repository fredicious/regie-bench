from __future__ import annotations

import argparse
import json
from collections.abc import Sequence


def add_item(items: Sequence[dict], name: str, quantity: int) -> list[dict]:
    """Return a new inventory with one validated item appended."""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("name must not be blank")
    if not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("quantity must be a positive integer")
    return [*items, {"name": clean_name, "quantity": quantity}]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inventory")
    parser.add_argument("name")
    parser.add_argument("quantity", type=int)
    args = parser.parse_args(argv)
    print(json.dumps(add_item([], args.name, args.quantity)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
