#!/usr/bin/env python3
"""
Build OISP Spec Bundle

Creates a single JSON bundle from the generated models.json that sensors can fetch
at runtime. This enables dynamic provider/model updates without recompiling.

The bundle includes (all from sync-models.py generated data):
1. Provider registry with api_format for each provider
2. Model registry with pricing, capabilities, families
3. Parsers for each API format (openai, anthropic, google, bedrock, cohere)
4. Domain lookup table for provider detection
5. Domain patterns for wildcard matching (Azure, Bedrock)

Output: dist/oisp-spec-bundle.json

Usage:
    python scripts/build-bundle.py
    python scripts/build-bundle.py --output ./custom-path.json
"""

import argparse
import json
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path

REGISTRY_ROOT = Path(__file__).parent.parent
PROVIDERS_DIR = REGISTRY_ROOT / "providers"
REGISTRY_DIR = REGISTRY_ROOT


def load_json(path: Path) -> dict:
    """Load a JSON file."""
    with open(path) as f:
        return json.load(f)


def load_registry_from_folder(folder_path: Path) -> tuple[str, dict]:
    """
    Load registry items from a folder structure.

    Structure:
        folder_path/
            _meta.json          # Optional, contains version
            <category>/
                <id>.json       # Individual item files

    Returns:
        (version, items_dict)
    """
    version = "1.0.0"
    items = {}

    if not folder_path.exists():
        return version, items

    # Load version from _meta.json if exists
    meta_path = folder_path / "_meta.json"
    if meta_path.exists():
        meta = load_json(meta_path)
        version = meta.get("version", version)

    # Load all JSON files from category subdirectories
    for category_dir in folder_path.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith("_"):
            continue

        for item_file in category_dir.glob("*.json"):
            item_id = item_file.stem  # filename without .json
            try:
                item_data = load_json(item_file)
                items[item_id] = item_data
            except Exception as e:
                print(f"Warning: Failed to load {item_file}: {e}", file=sys.stderr)

    return version, items


def load_registry() -> dict:
    """Load app and website registries from folder structure."""
    result = {"version": "1.0.0", "apps": {}, "websites": {}}

    # Load apps from apps/ folder
    apps_version, apps = load_registry_from_folder(REGISTRY_DIR / "apps")
    result["version"] = apps_version
    result["apps"] = apps

    # Load websites from websites/ folder
    _, websites = load_registry_from_folder(REGISTRY_DIR / "websites")
    result["websites"] = websites

    return result


def load_models() -> dict:
    """Load the generated models registry (source of truth)."""
    models_path = PROVIDERS_DIR / "_generated" / "models.json"
    if not models_path.exists():
        print(
            f"Error: {models_path} not found. Run sync-models.py first.",
            file=sys.stderr,
        )
        sys.exit(1)
    return load_json(models_path)


def build_bundle() -> dict:
    """Build the complete spec bundle from generated models.json."""
    models_data = load_models()
    registry_data = load_registry()

    bundle = {
        "$schema": "https://oisp.dev/schema/v0.1/bundle.schema.json",
        "version": models_data.get("version", "0.1"),
        "bundle_version": "2.1.0",  # Includes registry (apps + websites)
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "oisp-spec",
        "source_url": models_data.get("source_url", "https://models.dev/api.json"),
        "logos_url": models_data.get("logos_url", "https://models.dev/logos"),
        # Stats
        "stats": models_data.get("stats", {}),
        # Provider registry with api_format
        "providers": models_data.get("providers", {}),
        # Domain lookup for provider detection
        "domain_lookup": models_data.get("domain_lookup", {}),
        # Domain patterns for wildcard matching (Azure, Bedrock)
        "domain_patterns": models_data.get("domain_patterns", []),
        # Parsers for each API format
        "parsers": models_data.get("parsers", {}),
        # Model registry
        "models": models_data.get("models", {}),
        # App and website registry
        "registry": {
            "version": registry_data.get("version", "1.0.0"),
            "apps": registry_data.get("apps", {}),
            "websites": registry_data.get("websites", {}),
            "icons_url": "https://oisp.dev/registry/icons",
        },
    }

    return bundle


def main():
    parser = argparse.ArgumentParser(description="Build OISP Spec Bundle")
    parser.add_argument(
        "--output",
        type=Path,
        default=REGISTRY_ROOT / "dist" / "oximy-bundle.json",
        help="Output path for bundle",
    )
    parser.add_argument("--minify", action="store_true", help="Minify JSON output")
    args = parser.parse_args()

    # Build bundle
    print("Building OISP Spec Bundle...")
    bundle = build_bundle()

    # Create output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Write bundle
    indent = None if args.minify else 2
    with open(args.output, "w") as f:
        json.dump(bundle, f, indent=indent, sort_keys=True)

    # Print stats
    stats = bundle.get("stats", {})
    registry = bundle.get("registry", {})
    print(f"Bundle written to: {args.output}")
    print(f"  Version: {bundle['bundle_version']}")
    print(f"  Providers: {stats.get('providers', len(bundle['providers']))}")
    print(f"  Models: {stats.get('total_models', len(bundle['models']))}")
    print(f"  API Formats: {stats.get('api_formats', len(bundle['parsers']))}")
    print(f"  Domains indexed: {len(bundle['domain_lookup'])}")
    print(f"  Domain patterns: {len(bundle['domain_patterns'])}")
    print(f"  Parsers: {', '.join(bundle['parsers'].keys())}")
    print(f"  Apps: {len(registry.get('apps', {}))}")
    print(f"  Websites: {len(registry.get('websites', {}))}")

    # Also write a minified version
    if not args.minify:
        min_path = args.output.with_suffix(".min.json")
        with open(min_path, "w") as f:
            json.dump(bundle, f, separators=(",", ":"), sort_keys=True)
        print(f"  Minified: {min_path}")


if __name__ == "__main__":
    main()
