#!/usr/bin/env python3
"""Refresh openapi.json from the live SockOdds contract.

    python3 scripts/refresh_openapi.py           # download and write openapi.json
    python3 scripts/refresh_openapi.py --check   # exit 1 if openapi.json is out of date

Standard library only. The contract is public, so no key is needed.

Repair step: a few descriptions in the published contract contain a comma that
was split into extra keys with a null value, for example
    "description": "... individual sports (tennis",
    "mixed martial arts) use competitor_1 and competitor_2.": null
This script joins such keys back onto the description they were cut from
("..., mixed martial arts) use ..."). It also trims access notes to the plans
developers can buy (NOT_ON_SALE below). When the published contract has neither,
the repair changes nothing.
"""

import argparse
import json
import pathlib
import re
import sys
import urllib.request

SOURCE = "https://sockodds.com/openapi.json"
TARGET = pathlib.Path(__file__).resolve().parent.parent / "openapi.json"
NOT_ON_SALE = re.compile(r"\b(Pro|Rookie|Developer) and Internal only\b")


def repair(node):
    """Join null-valued keys that follow a description back onto it. Returns the number joined."""
    joined = 0
    if isinstance(node, dict):
        rebuilt = {}
        last_description = None
        for key, value in node.items():
            if value is None and last_description is not None:
                rebuilt[last_description] += ", " + key
                joined += 1
                continue
            rebuilt[key] = value
            last_description = key if key == "description" and isinstance(value, str) else None
        node.clear()
        node.update(rebuilt)
        for value in node.values():
            joined += repair(value)
    elif isinstance(node, list):
        for value in node:
            joined += repair(value)
    return joined


def public_plans(node):
    """Rewrite access notes to name only plans on sale. Returns the number rewritten."""
    count = 0
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str) and NOT_ON_SALE.search(value):
                node[key] = NOT_ON_SALE.sub(r"\1 only", value)
                count += 1
            else:
                count += public_plans(value)
    elif isinstance(node, list):
        for value in node:
            count += public_plans(value)
    return count


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "sockodds-api-refresh/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if openapi.json differs from the live contract")
    parser.add_argument("--source", default=SOURCE, help="contract URL (default: %(default)s)")
    args = parser.parse_args()

    spec = fetch(args.source)
    if not str(spec.get("openapi", "")).startswith("3.") or not spec.get("paths"):
        sys.exit(f"{args.source} did not return an OpenAPI 3 document")
    joined = repair(spec)
    plans = public_plans(spec)
    text = json.dumps(spec, indent=2, ensure_ascii=False) + "\n"

    operations = sum(
        1 for item in spec["paths"].values() for method in item if method in ("get", "post", "put", "patch", "delete")
    )
    summary = f"SockOdds API {spec['info']['version']}: {len(spec['paths'])} paths, {operations} operations"
    if joined:
        summary += f", {joined} split description fragment(s) rejoined"
    if plans:
        summary += f", {plans} access note(s) limited to public plans"

    current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
    if args.check:
        if current != text:
            print(f"openapi.json is out of date ({summary}). Run: python3 scripts/refresh_openapi.py")
            sys.exit(1)
        print(f"openapi.json is up to date ({summary})")
        return
    TARGET.write_text(text, encoding="utf-8")
    print(("Updated" if current != text else "Unchanged") + f" openapi.json ({summary})")


if __name__ == "__main__":
    main()
