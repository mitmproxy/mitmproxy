"""
This module provides a @concurrent decorator primitive to
offload computations from mitmproxy's main master thread.
"""
from __future__ import absolute_import, print_function, division
import threading


class ReplyProxy(object):
    def __init__(self, original_reply, script_thread):
        self.original_reply = original_reply
        self.script_thread = script_thread
        self._ignore_call = True
        self.lock = threading.Lock()

    def __call__(self, *args, **kwargs):
        with self.lock:
            if self._ignore_call:
                self.script_thread.start()
                self._ignore_call = False
                return
        self.original_reply(*args, **kwargs)

    def __getattr__(self, k):
        return getattr(self.original_reply, k)


def _handle_concurrent_reply(fn, o, *args, **kwargs):
    # Make first call to o.reply a no op and start the script thread.
    # We must not start the script thread before, as this may lead to a nasty race condition
    # where the script thread replies a different response before the normal reply, which then gets swallowed.

    def run():
        fn(*args, **kwargs)
        # If the script did not call .reply(), we have to do it now.
        reply_proxy()

    script_thread = ScriptThread(target=run)

    reply_proxy = ReplyProxy(o.reply, script_thread)
    o.reply = reply_proxy


class ScriptThread(threading.Thread):
    name = "ScriptThread"


def concurrent(fn):
    if fn.func_name in (
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
        "Concurrent decorator not supported for '%s' method." % fn.func_name)
