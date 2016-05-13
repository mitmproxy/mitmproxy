"""
This module provides a @concurrent decorator primitive to
offload computations from mitmproxy's main master thread.
"""
from __future__ import absolute_import, print_function, division
import threading


class ReplyProxy(object):

    def __init__(self, reply_func, script_thread):
        self.reply_func = reply_func
        self.script_thread = script_thread
        self.master_reply = None

    def __call__(self, *args):
        if self.master_reply is None:
            self.master_reply = args
            self.script_thread.start()
            return
        self.reply_func(*args)

    def done(self):
        self.reply_func(*self.master_reply)

    def __getattr__(self, k):
        return getattr(self.reply_func, k)


def _handle_concurrent_reply(fn, o, *args, **kwargs):
    # Make first call to o.reply a no op and start the script thread.
    # We must not start the script thread before, as this may lead to a nasty race condition
    # where the script thread replies a different response before the normal reply, which then gets swallowed.

    def run():
        fn(*args, **kwargs)
        # If the script did not call .reply(), we have to do it now.
        reply_proxy.done()

    script_thread = ScriptThread(target=run)

    reply_proxy = ReplyProxy(o.reply, script_thread)
    o.reply = reply_proxy


class ScriptThread(threading.Thread):
    name = "ScriptThread"


def concurrent(fn):
    if fn.__name__ in (
            "request",
            "response",
            "error",
            "clientconnect",
            "serverconnect",
            "clientdisconnect",
            "next_layer"):
        def _concurrent(ctx, obj):
            _handle_concurrent_reply(fn, obj, ctx, obj)

        return _concurrent
    raise NotImplementedError(
        "Concurrent decorator not supported for '%s' method." % fn.__name__)
