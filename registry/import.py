#!/usr/bin/env python3
"""
Import app or website definitions into the registry.

Usage:
    python import.py -app              # Import import.json as app
    python import.py -web              # Import import.json as website
    python import.py -app myfile.json  # Import specific file as app
    python import.py -web myfile.json  # Import specific file as website

The input JSON file must have an "id" field which will be used as the filename.
The "category" field determines which subdirectory the file is placed in.

Structure:
    apps/<category>/<id>.json
    websites/<category>/<id>.json
"""

import argparse
import json
import sys
from pathlib import Path

DEFAULT_INPUT = "import.json"


def load_json(path: Path) -> dict:
    """Load and parse a JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)


def save_json(path: Path, data: dict) -> None:
    """Save data to a JSON file with pretty formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def import_entry(input_path: Path, registry_dir: Path) -> None:
    """
    Import an entry into the registry folder structure.

    Args:
        input_path: Path to the input JSON file
        registry_dir: Path to the registry folder (apps/ or websites/)
    """
    # Load the input file
    entry = load_json(input_path)

    # Validate required fields
    if "id" not in entry:
        print("Error: Input JSON must have an 'id' field", file=sys.stderr)
        sys.exit(1)

    entry_id = entry["id"]
    category = entry.get("category", "other")

    # Remove the id field from the entry data (it becomes the filename)
    entry_data = {k: v for k, v in entry.items() if k != "id"}

    # Determine output path
    output_path = registry_dir / category / f"{entry_id}.json"

    # Check if entry already exists
    if output_path.exists():
        print(f"Error: Entry already exists at {output_path}", file=sys.stderr)
        print("Remove it first if you want to replace it.", file=sys.stderr)
        sys.exit(1)

    # Save the entry
    save_json(output_path, entry_data)

    print(f"Imported '{entry_id}' into {output_path.relative_to(registry_dir.parent)}")
    print(f"  Name: {entry_data.get('name', 'N/A')}")
    print(f"  Vendor: {entry_data.get('vendor', 'N/A')}")
    print(f"  Category: {category}")

    if "features" in entry_data:
        features = list(entry_data["features"].keys())
        print(f"  Features: {', '.join(features)}")


def main():
    parser = argparse.ArgumentParser(
        description="Import app or website definitions into the registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python import.py -app              # Import import.json as app
    python import.py -web              # Import import.json as website
    python import.py -app claude.json  # Import specific file as app
    python import.py -web perplexity.json

Structure:
    Apps are saved to:     registry/apps/<category>/<id>.json
    Websites are saved to: registry/websites/<category>/<id>.json
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-app",
        nargs="?",
        const=DEFAULT_INPUT,
        metavar="FILE",
        help=f"Import as an app into apps/ (default: {DEFAULT_INPUT})",
    )
    group.add_argument(
        "-web",
        nargs="?",
        const=DEFAULT_INPUT,
        metavar="FILE",
        help=f"Import as a website into websites/ (default: {DEFAULT_INPUT})",
    )

    args = parser.parse_args()

    # Determine paths
    script_dir = Path(__file__).parent

    if args.app:
        input_file = args.app
        registry_dir = script_dir / "apps"
    else:
        input_file = args.web
        registry_dir = script_dir / "websites"

    # Resolve input path
    input_path = Path(input_file)
    if not input_path.is_absolute():
        # First check relative to script dir (registry/)
        if (script_dir / input_path).exists():
            input_path = script_dir / input_path
        else:
            # Then check relative to cwd
            input_path = Path.cwd() / input_path

    # Verify input exists
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    import_entry(input_path, registry_dir)


if __name__ == "__main__":
    main()
