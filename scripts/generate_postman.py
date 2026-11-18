#!/usr/bin/env python3
"""Generate the Postman collection from openapi.json.

    python3 scripts/generate_postman.py           # write sockodds-api-v1.postman_collection.json
    python3 scripts/generate_postman.py --check   # exit 1 if the collection is out of date

Standard library only. The output is deterministic, so regenerating an unchanged
spec gives a byte-identical file.

The collection has one folder per tag and one request per HTTP operation. Two
collection variables drive every request:

    baseUrl      https://api.sockodds.com/v1 (filled in)
    sockoddsKey  your SockOdds key (empty: set it as the current value in Postman)

Authentication is set once on the collection (Bearer {{sockoddsKey}}). Required
query parameters are enabled; optional ones are listed but disabled, so you can
tick the ones you want. Every id, date and key in the example values is a
placeholder: replace it with values from your own responses.

The odds stream (GET /stream/odds) is a WebSocket upgrade, which a Postman
collection cannot describe, so it is left out. See https://sockodds.com/docs/streaming/.
"""

import argparse
import json
import pathlib
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = ROOT / "openapi.json"
TARGET = ROOT / "sockodds-api-v1.postman_collection.json"
DOCS = "https://sockodds.com/docs/"

# Placeholder values for parameters. Ids are invented sample ids in the right format.
SAMPLES = {
    "event_id": "ev_0000000000a1",
    "race_id": "thoroughbred_2026-01-01_AUS_samplemeeting_r1",
    "league": "nfl",
    "sport": "american_football",
    "team": "team_key",
    "markets": "winner",
    "regions": "au",
    "bookmakers": "bookmaker_key_1,bookmaker_key_2",
    "alternates": "false",
    "group_by": "market",
    "non_participant": "void",
    "snapshots": "opening,closing",
    "starts_after": "2026-01-01T00:00:00Z",
    "starts_before": "2026-01-02T00:00:00Z",
    "from": "2026-01-01T00:00:00Z",
    "to": "2026-01-01T08:00:00Z",
    "day": "2026-01-01",
    "source": "espn",
    "ref": "401000001",
    "refs": "401000001,401000002",
    "code": "thoroughbred",
    "country": "AUS",
    "cursor": "",
}


def resolve(spec, node):
    while isinstance(node, dict) and "$ref" in node:
        target = spec
        for part in node["$ref"].lstrip("#/").split("/"):
            target = target[part]
        node = target
    return node


def sample_for(spec, param):
    name = param["name"]
    schema = resolve(spec, param.get("schema", {}))
    if name in SAMPLES:
        return SAMPLES[name]
    if "default" in schema:
        value = schema["default"]
        return str(value).lower() if isinstance(value, bool) else str(value)
    return ""


def first_sentence(text):
    text = (text or "").strip()
    end = text.find(". ")
    return text if end == -1 else text[: end + 1]


def build_request(spec, path, method, operation, path_params):
    params = [resolve(spec, p) for p in path_params + operation.get("parameters", [])]
    op_id = operation["operationId"]
    segments = [seg.strip("/") for seg in path.strip("/").split("/")]
    url_path = [":" + seg[1:-1] if seg.startswith("{") else seg for seg in segments]

    # The contract's own example query, where it gives one, is enabled as sent.
    example = dict(pair.split("=", 1) for pair in operation.get("x-example-query", "").split("&") if "=" in pair)

    query, variables = [], []
    for param in params:
        description = param.get("description", "")
        if param.get("required"):
            description = ("Required. " + description).strip()
        value = example.get(param["name"], sample_for(spec, param))
        entry = {"key": param["name"], "value": value, "description": description}
        if param["in"] == "path":
            variables.append(entry)
        elif param["in"] == "query":
            if not param.get("required") and param["name"] not in example:
                entry["disabled"] = True
            query.append(entry)

    raw_query = "&".join(f"{q['key']}={q['value']}" for q in query if not q.get("disabled"))
    raw = "{{baseUrl}}/" + "/".join(url_path) + (("?" + raw_query) if raw_query else "")
    url = {"raw": raw, "host": ["{{baseUrl}}"], "path": url_path}
    if query:
        url["query"] = query
    if variables:
        url["variable"] = variables

    description = (operation.get("description") or "").strip()
    description += f"\n\nReference: {DOCS}#{op_id}"
    return {
        "name": op_id,
        "request": {
            "method": method.upper(),
            "header": [{"key": "Accept", "value": "application/json"}],
            "url": url,
            "description": description.strip(),
        },
        "response": [],
    }


def build(spec):
    tags = [t["name"] for t in spec.get("tags", [])]
    tag_descriptions = {t["name"]: t.get("description", "") for t in spec.get("tags", [])}
    folders = {name: [] for name in tags}
    skipped = []
    for path, item in spec["paths"].items():
        path_params = item.get("parameters", [])
        for method, operation in item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            if "101" in operation.get("responses", {}):
                skipped.append(operation["operationId"])
                continue
            tag = (operation.get("tags") or ["Other"])[0]
            folders.setdefault(tag, []).append(build_request(spec, path, method, operation, path_params))

    items = []
    for name, requests in folders.items():
        if not requests:
            continue
        description = tag_descriptions.get(name, "")
        if name == "Prices" and skipped:
            description = (description + " The odds stream is a WebSocket, so it is not in this collection: "
                           "see https://sockodds.com/docs/streaming/.").strip()
        folder = {"name": name, "item": requests}
        if description:
            folder["description"] = description
        items.append(folder)

    info = spec["info"]
    servers = spec.get("servers") or [{"url": "https://api.sockodds.com/v1"}]
    return {
        "info": {
            "_postman_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/jameselle/sockodds-api")),
            "name": "SockOdds API v1",
            "description": (
                f"{info.get('description', '').strip()}\n\n"
                "Generated from openapi.json by scripts/generate_postman.py "
                f"(contract version {info['version']}).\n\n"
                "Set the `sockoddsKey` collection variable to your key, as the current value only, "
                "so it is never shared or exported. Get a free key at https://sockodds.com/signup/.\n\n"
                "Ids, dates and keys in the example values are placeholders: replace them with values "
                "from your own responses."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{sockoddsKey}}", "type": "string"}]},
        "variable": [
            {"key": "baseUrl", "value": servers[0]["url"], "type": "string"},
            {"key": "sockoddsKey", "value": "", "type": "string"},
        ],
        "item": items,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the collection is out of date")
    args = parser.parse_args()

    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    collection = build(spec)
    text = json.dumps(collection, indent=2, ensure_ascii=False) + "\n"
    count = sum(len(folder["item"]) for folder in collection["item"])
    current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
    if args.check:
        if current != text:
            print(f"{TARGET.name} is out of date. Run: python3 scripts/generate_postman.py")
            sys.exit(1)
        print(f"{TARGET.name} is up to date ({count} requests)")
        return
    TARGET.write_text(text, encoding="utf-8")
    print(f"{'Updated' if current != text else 'Unchanged'} {TARGET.name} ({count} requests in {len(collection['item'])} folders)")


if __name__ == "__main__":
    main()
