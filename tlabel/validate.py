"""
TLabel Schema Validator

Standalone utility for validating TLabel JSON files against the official schema.

Usage:
    python -m tlabel.validate path/to/file.json
    python -m tlabel.validate data/  # validate all .json in directory

Exit codes:
    0 = all files valid
    1 = validation errors found
    2 = missing dependencies (install jsonschema)
"""

import json
import sys
from pathlib import Path
from typing import Tuple

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "tlabel-schema.json"


def load_schema() -> dict:
    """Load the TLabel JSON schema."""
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def validate_file(filepath: str, schema: dict) -> Tuple[bool, list]:
    """
    Validate a single JSON file against the schema.

    Returns:
        (is_valid, list_of_errors)
    """
    try:
        import jsonschema
    except ImportError:
        print("ERROR: jsonschema not installed. Run: pip install jsonschema")
        sys.exit(2)

    errors = []
    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]

    validator = jsonschema.Draft7Validator(schema)
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.path) or "(root)"
        errors.append(f"  [{path}] {error.message}")

    return len(errors) == 0, errors


def validate_path(path: str) -> int:
    """
    Validate a file or all JSON files in a directory.

    Returns:
        Number of files with errors.
    """
    schema = load_schema()
    target = Path(path)

    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(target.glob("**/*.json"))
    else:
        print(f"ERROR: {path} does not exist")
        return 1

    if not files:
        print(f"No JSON files found in {path}")
        return 0

    error_count = 0
    for f in files:
        is_valid, errors = validate_file(str(f), schema)
        status = "✓ PASS" if is_valid else "✗ FAIL"
        print(f"{status}: {f}")
        if errors:
            error_count += 1
            for err in errors:
                print(err)

    total = len(files)
    passed = total - error_count
    print(f"\n{passed}/{total} files passed validation.")
    return error_count


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    error_count = 0
    for path in sys.argv[1:]:
        error_count += validate_path(path)

    sys.exit(1 if error_count > 0 else 0)


if __name__ == "__main__":
    main()
