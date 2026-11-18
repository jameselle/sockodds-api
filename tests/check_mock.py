#!/usr/bin/env python3
"""Check every mock route against the response schemas in openapi.json.

    pip install "jsonschema>=4.18"
    python3 tests/check_mock.py

Starts mock/server.py on a free port, requests each route the examples use, and
validates the body against the operation's documented 200 response schema (or
the Problem schema for errors). Exits non-zero on the first mismatch.
"""

import json
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
except ImportError:
    sys.exit('tests/check_mock.py needs jsonschema: pip install "jsonschema>=4.18"')

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = json.loads((ROOT / "openapi.json").read_text(encoding="utf-8"))
KEY = "sample-key-not-real"

# (request path and query, operationId, expected status)
CASES = [
    ("/sports", "listSports", 200),
    ("/leagues", "listLeagues", 200),
    ("/bookmakers", "listBookmakers", 200),
    ("/markets?league=sample_league&limit=100", "listMarkets", 200),
    ("/events?league=sample_league", "listEvents", 200),
    ("/events/ev_0000000000a1", "getEvent", 200),
    ("/events/ev_0000000000a1/odds", "getEventOdds", 200),
    ("/events/ev_0000000000a1/odds?markets=winner&snapshots=opening,closing", "getEventOdds", 200),
    ("/odds?league=sample_league&limit=25", "listOdds", 200),
    ("/odds?league=sample_league&limit=25&cursor=1", "listOdds", 200),
    ("/odds?league=other_league", "listOdds", 200),
    ("/odds/history?event_id=ev_0000000000a1&from=2026-12-05T00:00:00Z&to=2026-12-05T08:00:00Z", "listOddsHistory", 200),
    ("/odds/history?event_id=ev_0000000000a1&from=2026-12-05T00:00:00Z&to=2026-12-05T08:00:00Z&cursor=16",
     "listOddsHistory", 200),
    ("/results?event_id=ev_0000000000b1", "listResults", 200),
    ("/events/ev_0000000000zz", "getEvent", 404),
    ("/odds/history?event_id=ev_0000000000a1", "listOddsHistory", 400),
]


def operation_pointer(op_id):
    for path, item in SPEC["paths"].items():
        for method, op in item.items():
            if isinstance(op, dict) and op.get("operationId") == op_id:
                return "/paths/" + path.replace("~", "~0").replace("/", "~1") + "/" + method, op
    raise KeyError(op_id)


def response_schema(op_id, status):
    """A $ref (into the registered contract) to the schema documented for this status."""
    if status >= 400:
        return {"$ref": "urn:sockodds-openapi#/components/schemas/Problem"}
    pointer, op = operation_pointer(op_id)
    pointer, response = pointer + f"/responses/{status}", op["responses"][str(status)]
    if "$ref" in response:
        pointer = response["$ref"].lstrip("#")
        response = SPEC
        for part in pointer.strip("/").split("/"):
            response = response[part]
    media = "application/json" if "application/json" in response["content"] else next(iter(response["content"]))
    return {"$ref": "urn:sockodds-openapi#" + pointer + "/content/" + media.replace("/", "~1") + "/schema"}


def main():
    registry = Registry().with_resource("urn:sockodds-openapi", Resource.from_contents(
        {**SPEC, "$schema": "https://json-schema.org/draft/2020-12/schema"}))
    mock = subprocess.Popen([sys.executable, str(ROOT / "mock" / "server.py"), "--port", "0"],
                            stdout=subprocess.PIPE, text=True)
    try:
        base = mock.stdout.readline().strip().split(" on ")[-1]
        failures = 0
        for path, op_id, expected in CASES:
            request = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + KEY})
            try:
                with urllib.request.urlopen(request) as response:
                    status, body = response.status, json.load(response)
            except urllib.error.HTTPError as error:
                status, body = error.code, json.load(error)
            schema = response_schema(op_id, status)
            validator = Draft202012Validator(schema, registry=registry)
            errors = sorted(validator.iter_errors(body), key=lambda e: list(e.path))
            # The contract's odds envelopes are a oneOf of the two groupings, and an empty page
            # is valid under both. That is an ambiguity in the contract, not a mock error.
            if body.get("data") == []:
                errors = [e for e in errors if not (e.validator == "oneOf" and not e.path)]
            ok = status == expected and not errors
            failures += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {status} {op_id:16} {path}")
            for error in errors[:5]:
                print(f"       {'/'.join(map(str, error.path))}: {error.message[:200]}")
        unauth = urllib.request.Request(base + "/sports")
        try:
            urllib.request.urlopen(unauth)
            print("FAIL no key was accepted")
            failures += 1
        except urllib.error.HTTPError as error:
            print(f"{'ok  ' if error.code == 401 else 'FAIL'} {error.code} no key           /sports")
            failures += error.code != 401
    finally:
        mock.terminate()
        mock.wait()
    print(f"{len(CASES) + 1 - failures}/{len(CASES) + 1} mock responses match openapi.json")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
