"""
This module provides a @concurrent decorator primitive to
offload computations from mitmproxy's main master thread.
"""
from __future__ import absolute_import, print_function, division

from mitmproxy import controller
from netlib import basethread


class ScriptThread(basethread.BaseThread):
    name = "ScriptThread"


def concurrent(fn):
    if fn.__name__ not in controller.Events - {"start", "configure", "tick"}:
        raise NotImplementedError(
            "Concurrent decorator not supported for '%s' method." % fn.__name__
        )

    def _concurrent(obj):
        def run():
            fn(obj)
            if obj.reply.state == "taken":
                if not obj.reply.has_message:
                    obj.reply.ack()
                obj.reply.commit()
        obj.reply.take()
        ScriptThread(
            "script.concurrent (%s)" % fn.__name__,
            target=run
        ).start()
    return _concurrent
