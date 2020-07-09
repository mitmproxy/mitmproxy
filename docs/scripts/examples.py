#!/usr/bin/env python3

import re
from pathlib import Path

here = Path(__file__).absolute().parent
example_dir = here / ".." / "src" / "examples" / "addons"
examples = example_dir.glob('*.py')

overview = []
listings = []

for example in examples:
    code = example.read_text()
    slug = str(example.with_suffix("").relative_to(example_dir))
    slug = re.sub(r"[^a-zA-Z]", "-", slug)
    match = re.search(r'''
        ^
        (?:[#][^\n]*\n)?  # there might be a shebang
        """
        \s*
        (.+?)
        \s*
        (?:\n\n|""")     # stop on empty line or end of comment
    ''', code, re.VERBOSE)
    if match:
        comment = " — " + match.group(1)
    else:
        comment = ""
    overview.append(
        f"  * [{example.name}](#{slug}){comment}"
    )
    listings.append(f"""
<h2 id="{slug}">Example: {example.name}</h2>

```python
{code}
```
""")
print("\n".join(overview))
print("""
### Community Examples

Additional examples contributed by the mitmproxy community can be found
[on GitHub](https://github.com/mitmproxy/mitmproxy/tree/master/examples/contrib).

""")
print("\n".join(listings))
