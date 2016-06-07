"""
This module provides a @concurrent decorator primitive to
offload computations from mitmproxy's main master thread.
"""
from __future__ import absolute_import, print_function, division

from mitmproxy import controller
import threading


class ScriptThread(threading.Thread):
    name = "ScriptThread"


def concurrent(fn):
    if fn.__name__ not in controller.Events:
        raise NotImplementedError(
            "Concurrent decorator not supported for '%s' method." % fn.__name__
        )

    def _concurrent(ctx, obj):
        def run():
            fn(ctx, obj)
            if not obj.reply.acked:
                obj.reply.ack()
        obj.reply.take()
        ScriptThread(target=run).start()
    return _concurrent
