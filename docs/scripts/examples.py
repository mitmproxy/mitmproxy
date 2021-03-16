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
        f"  * [{example.name}](#{slug}){comment}\n"
    )
    listings.append(f"""
<h3 id="{slug}">Example: {example.name}</h3>

```python
{code.strip()}
```
""")

print(f"""
# Addon Examples

### Dedicated Example Addons

{"".join(overview)}

### Built-In Addons

Much of mitmproxy’s own functionality is defined in
[a suite of built-in addons](https://github.com/mitmproxy/mitmproxy/tree/main/mitmproxy/addons),
implementing everything from functionality like anticaching and sticky cookies to our onboarding webapp.
The built-in addons make for instructive reading, and you will quickly see that quite complex functionality
can often boil down to a very small, completely self-contained modules.


### Additional Community Examples

Additional examples contributed by the mitmproxy community can be found
[on GitHub](https://github.com/mitmproxy/mitmproxy/tree/main/examples/contrib).

-------------------------

{"".join(listings)}
""")
