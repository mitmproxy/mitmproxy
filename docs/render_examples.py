#!/usr/bin/env python3

import os
import textwrap
from pathlib import Path

print("""
---
title: "Examples"
menu:
    addons:
        weight: 6
---

# Examples of Addons and Scripts

The most recent set of examples is also available [on our GitHub project](https://github.com/mitmproxy/mitmproxy/tree/master/examples).

""")

base = os.path.dirname(os.path.realpath(__file__))
examples_path = os.path.join(base, 'src/examples/')
pathlist = Path(examples_path).glob('**/*.py')

examples = [os.path.relpath(str(p), examples_path) for p in sorted(pathlist)]
examples = [p for p in examples if not os.path.basename(p) == '__init__.py']
examples = [p for p in examples if not os.path.basename(p).startswith('test_')]

current_dir = None
current_level = 2
for ex in examples:
    if os.path.dirname(ex) != current_dir:
        current_dir = os.path.dirname(ex)
        sanitized = current_dir.replace('/', '').replace('.', '')
        print("  * [Examples: {}]({{{{< relref \"addons-examples#{}\">}}}})".format(current_dir, sanitized))

    sanitized = ex.replace('/', '').replace('.', '')
    print("    * [{}]({{{{< relref \"addons-examples#example-{}\">}}}})".format(os.path.basename(ex), sanitized))

current_dir = None
current_level = 2
for ex in examples:
    if os.path.dirname(ex) != current_dir:
        current_dir = os.path.dirname(ex)
        print("#" * current_level, current_dir)

    print(textwrap.dedent("""
        {} Example: {}
        {{{{< example src="{}" lang="py" >}}}}
    """.format("#" * (current_level + 1), ex, "examples/" + ex)))
