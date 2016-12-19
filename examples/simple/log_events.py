"""
It is recommended to use `ctx.log` for logging within a script.
This goes to the event log in mitmproxy and to stdout in mitmdump.

If you want to help us out: https://github.com/mitmproxy/mitmproxy/issues/1530 :-)
"""
from mitmproxy import ctx


def start():
    ctx.log.info("This is some informative text.")
    ctx.log.error("This is an error.")
