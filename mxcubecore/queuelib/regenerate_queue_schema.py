#!/usr/bin/env python3
"""Regenerate the checked-in queue JSON schema snapshot.

This script reads the live Pydantic models in mxcubecore.queuelib and writes the
serialized schema to mxcubecore/queuelib/queue.schema.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from mxcubecore.queuelib.json_schema import get_json_schema


def main() -> None:
    schema = get_json_schema()
    schema_path = (
        Path(__file__).resolve().parent
        / "mxcubecore"
        / "queuelib"
        / "queue.schema.json"
    )
    schema_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {schema_path}")


if __name__ == "__main__":
    main()
