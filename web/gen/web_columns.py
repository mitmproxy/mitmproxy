#!/usr/bin/env python3
import asyncio
import json
import re
from pathlib import Path


def extract_flow_columns():
    here = Path(__file__).parent.absolute()
    filename = here / "../src/js/components/FlowTable/FlowColumns.tsx"
    with open(filename, "r") as file:
        content = file.read()
    pattern = r"const FlowColumns:.*?=\s*{([^}]*)}"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        columns_text = match.group(1)
        columns_text = re.sub(r"//.*$", "", columns_text, flags=re.MULTILINE)
        columns = re.findall(r"\b(\w+),?", columns_text)
        return columns
    return []


filename = Path("mitmproxy/tools/web/web_columns.py")


async def make():
    AVAILABLE_WEB_COLUMNS = extract_flow_columns()
    output = f"""
# Auto-generated by generate_web_columns.py
AVAILABLE_WEB_COLUMNS = {json.dumps(AVAILABLE_WEB_COLUMNS, indent=4)}
"""
    return output.strip()


if __name__ == "__main__":
    content = asyncio.run(make())
    filename.write_text(content)