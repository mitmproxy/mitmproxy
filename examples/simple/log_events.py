"""
It is recommended to use `ctx.log` for logging within a script.
print() statements are equivalent to ctx.log.warn().
"""
from mitmproxy import ctx


def load(l):
    ctx.log.info("This is some informative text.")
    ctx.log.error("This is an error.")
