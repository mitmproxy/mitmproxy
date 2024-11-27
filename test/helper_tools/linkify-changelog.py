#!/usr/bin/env python3
import re
from pathlib import Path

changelog = Path(__file__).parent / "../../CHANGELOG.md"

text = changelog.read_text(encoding="utf8")
text, n = re.subn(
    r"\s*\(([^)]+)#(\d+)\)",
    "\n  (\\1[#\\2](https://github.com/mitmproxy/mitmproxy/issues/\\2))",
    text,
)
changelog.write_text(text, encoding="utf8")
print(f"Linkified {n} issues and users.")
