#!/usr/bin/env python3
"""
Pre-commit hook to prevent DEV mode settings from being committed.

This script checks for dangerous patterns that should never be in production:
1. Hardcoded OXIMY_AUTO_PROXY_ENABLED = True (must use config)
2. Hardcoded localhost API URLs (must be commented out)
3. Uncommented localhost URLs in Swift/C#

Exit codes:
- 0: All checks passed
- 1: Dangerous patterns found

Usage:
    python scripts/check_dev_mode.py [files...]

    If no files specified, checks all relevant files in the repo.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Patterns that are NEVER allowed to be committed (with their error messages)
FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    # Python: Hardcoded auto proxy (must use config.AUTO_PROXY_ENABLED)
    (
        r"^OXIMY_AUTO_PROXY_ENABLED\s*=\s*True\s*$",
        "OXIMY_AUTO_PROXY_ENABLED must not be hardcoded to True. Use config.AUTO_PROXY_ENABLED",
    ),
    # Python: Hardcoded localhost in production code
    (
        r'(?:API_URL|api_url|apiUrl)\s*=\s*["\']http://localhost',
        "Localhost API URLs must not be committed. Use config or environment variables",
    ),
    # Swift: Uncommented localhost API endpoint
    (
        r'^[^/]*defaultAPIEndpoint\s*=\s*"http://localhost',
        "Swift: defaultAPIEndpoint must not be localhost. Comment it out or use config",
    ),
    # C#: Uncommented localhost API URL
    (
        r'^[^/]*ApiBaseUrl\s*=\s*"http://localhost',
        "C#: ApiBaseUrl must not be localhost. Keep it commented out",
    ),
]

# Files/directories that are ALLOWED to have these patterns
ALLOWED_PATHS: set[str] = {
    "check_dev_mode.py",  # This script contains patterns as strings
    "test_",  # Test files may test dev mode
    "tests/",  # Test directories
    "CLAUDE.md",  # Documentation
    "README.md",  # Documentation
    "DEV_MODE.md",  # Documentation
    ".claude/",  # Claude plans/notes
}


def is_allowed_file(filepath: Path) -> bool:
    """Check if file is in the allowed list."""
    path_str = str(filepath)
    name = filepath.name

    for allowed in ALLOWED_PATHS:
        if allowed in path_str or name.startswith(allowed):
            return True
    return False


def check_file(filepath: Path) -> list[str]:
    """Check a single file for forbidden patterns.

    Returns list of error messages (empty if file is clean).
    """
    errors: list[str] = []

    if is_allowed_file(filepath):
        return errors

    # Only check relevant file types
    suffix = filepath.suffix.lower()
    if suffix not in {".py", ".swift", ".cs"}:
        return errors

    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return errors

    for line_num, line in enumerate(content.splitlines(), start=1):
        # Skip comment lines
        stripped = line.lstrip()
        if stripped.startswith(("#", "//", "/*", "*", "///")):
            continue

        for pattern, message in FORBIDDEN_PATTERNS:
            if re.search(pattern, line):
                errors.append(f"{filepath}:{line_num}: {message}")
                errors.append(f"    Found: {line.strip()}")

    return errors


def find_files_to_check() -> list[Path]:
    """Find all relevant files in the repository."""
    repo_root = Path(__file__).parent.parent
    files: list[Path] = []

    for pattern in ["**/*.py", "**/*.swift", "**/*.cs"]:
        for filepath in repo_root.glob(pattern):
            # Skip build artifacts and dependencies
            path_str = str(filepath)
            if any(
                skip in path_str
                for skip in [
                    ".build/",
                    "/build/",
                    "node_modules/",
                    "__pycache__/",
                    ".tox/",
                    "venv/",
                    ".venv/",
                    "DerivedData/",
                ]
            ):
                continue
            files.append(filepath)

    return files


def main() -> int:
    """Main entry point."""
    # Get files to check
    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:] if Path(f).exists()]
    else:
        files = find_files_to_check()

    all_errors: list[str] = []

    for filepath in files:
        errors = check_file(filepath)
        all_errors.extend(errors)

    if all_errors:
        print("\n" + "=" * 60)
        print("DEV MODE SAFETY CHECK FAILED!")
        print("=" * 60 + "\n")

        for error in all_errors:
            print(f"  {error}")

        print("\n" + "=" * 60)
        print("These patterns must never be committed to production.")
        print("")
        print("For local development, use one of:")
        print("  1. Environment variable: export OXIMY_DEV=1")
        print("  2. Config file: ~/.oximy/dev.json")
        print("=" * 60 + "\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
