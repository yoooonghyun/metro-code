#!/usr/bin/env python3
"""Manage price-target alerts.

Usage:
    targets.py set <SYMBOL> <PRICE> [above|below]
    targets.py list
    targets.py remove <SYMBOL> [<SYMBOL> ...]
    targets.py clear

`set` fetches the current price (through the shared cache) and, if no direction
is given, auto-detects it: target above the current price -> "above" (alert when
the price rises to touch it); target below -> "below". Setting a target re-arms
it (clears the fired flag). monitor.py fires the alert when the target is
touched; statusline.py shows a 🔔 next to a touched symbol.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    load_targets, save_targets, load_aliases, get_quotes, format_price,
    display_name,
)


def cmd_set(args):
    if len(args) < 2:
        print("Usage: targets.py set <SYMBOL> <PRICE> [above|below]")
        return 1
    sym = args[0].strip().upper()
    try:
        price = float(args[1].replace(",", ""))
    except ValueError:
        print(f"Invalid price: {args[1]}")
        return 1
    direction = args[2].lower() if len(args) >= 3 else None
    if direction not in (None, "above", "below"):
        print("Direction must be 'above' or 'below'.")
        return 1

    q = get_quotes([sym]).get(sym)
    if not q:
        print(f"Could not fetch a current price for {sym} (symbol may not exist).")
        return 1
    current = q["price"]
    if direction is None:
        direction = "above" if price >= current else "below"

    name = display_name(sym, q)   # store the auto name; alias resolved at display time
    label = display_name(sym, q, load_aliases().get(sym))
    targets = load_targets()
    targets[sym] = {"price": price, "direction": direction, "fired": False, "name": name}
    save_targets(targets)
    arrow = "↑" if direction == "above" else "↓"
    print(f"Target set: {label} {arrow} {format_price(sym, price)} "
          f"(now {format_price(sym, current)})")
    return 0


def cmd_list():
    targets = load_targets()
    if not targets:
        print("No price targets set.")
        return 0
    aliases = load_aliases()
    print("Price targets:")
    for sym, t in targets.items():
        arrow = "↑" if t["direction"] == "above" else "↓"
        state = "fired" if t.get("fired") else "armed"
        label = aliases.get(sym) or t.get("name") or sym
        print(f"  - {label} {arrow} {format_price(sym, t['price'])}  [{state}]")
    return 0


def cmd_remove(symbols):
    targets = load_targets()
    removed = []
    for raw in symbols:
        sym = raw.strip().upper()
        if sym in targets:
            del targets[sym]
            removed.append(sym)
    save_targets(targets)
    if removed:
        for s in removed:
            print(f"Removed target: {s}")
    else:
        print("No matching targets.")
    return 0


def cmd_clear():
    save_targets({})
    print("Cleared all price targets.")
    return 0


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    cmd, rest = argv[0], argv[1:]
    if cmd == "set":
        return cmd_set(rest)
    if cmd == "list":
        return cmd_list()
    if cmd == "remove":
        if not rest:
            print("Usage: targets.py remove <SYMBOL> ...")
            return 1
        return cmd_remove(rest)
    if cmd == "clear":
        return cmd_clear()
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
