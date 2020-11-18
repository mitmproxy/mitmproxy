import os
import sys

import warnings

warnings.warn(
    "pathod and pathoc modules are deprecated, see https://github.com/mitmproxy/mitmproxy/issues/4273",
    DeprecationWarning,
    stacklevel=2
)


def print_tool_deprecation_message():
    print("####", file=sys.stderr)
    print(f"### {os.path.basename(sys.argv[0])} is deprecated and will not be part of future mitmproxy releases!", file=sys.stderr)
    print("### See https://github.com/mitmproxy/mitmproxy/issues/4273 for more information.", file=sys.stderr)
    print("####", file=sys.stderr)
    print("", file=sys.stderr)
