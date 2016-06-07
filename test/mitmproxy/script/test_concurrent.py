from mitmproxy.script import Script
from test.mitmproxy import tutils
from mitmproxy import controller
import time


class Thing:
    def __init__(self):
        self.reply = controller.DummyReply()


@tutils.skip_appveyor
def test_concurrent():
    with Script(tutils.test_data.path("data/scripts/concurrent_decorator.py"), None) as s:
        f1, f2 = Thing(), Thing()
        s.run("request", f1)
        s.run("request", f2)
        start = time.time()
        while time.time() - start < 5:
            if f1.reply.acked and f2.reply.acked:
                return
        raise ValueError("Script never acked")


def test_concurrent_err():
    s = Script(tutils.test_data.path("data/scripts/concurrent_decorator_err.py"), None)
    with tutils.raises("Concurrent decorator not supported for 'start' method"):
        s.load()
