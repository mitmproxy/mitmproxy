"""
This example shows how addons can register custom options
that can be configured at startup or during execution
from the options dialog within mitmproxy.

Example:

$ mitmproxy --set custom=true
$ mitmproxy --set custom   # shorthand for boolean options
"""
from mitmproxy import ctx


def load(l):
    ctx.log.info("Registering option 'custom'")
    l.add_option("custom", bool, False, "A custom option")


def configure(updated):
    if "custom" in updated:
        ctx.log.info("custom option value: %s" % ctx.options.custom)
