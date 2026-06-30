#!/usr/bin/env python3
"""Validate FTS JSON documents against the FTS schema.

Usage:
    python scripts/validate_schema.py \
        --schema engine/FarmTwin/schemas/fts_survey_schema.json \
        --docs   docs/examples/eruthempathy_pilot.fts.json [more...]
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("ERROR: pip install jsonschema", file=sys.stderr)
    sys.exit(1)


def validate(schema_path: str, doc_paths: list[str]) -> bool:
    schema = json.loads(Path(schema_path).read_text())
    validator = jsonschema.Draft7Validator(schema)
    all_ok = True
    for doc_path in doc_paths:
        doc = json.loads(Path(doc_path).read_text())
        errors = list(validator.iter_errors(doc))
        if errors:
            print(f"FAIL  {doc_path}: {len(errors)} error(s)")
            for e in errors:
                print(f"      [{'.'.join(str(p) for p in e.path)}] {e.message}")
            all_ok = False
        else:
            print(f"PASS  {doc_path}")
    return all_ok


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--schema", required=True)
    p.add_argument("--docs",   nargs="+", required=True)
    args = p.parse_args()
    sys.exit(0 if validate(args.schema, args.docs) else 1)


if __name__ == "__main__":
    main()
