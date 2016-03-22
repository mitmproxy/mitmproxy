from threading import Event

from mitmproxy.script import Script
from test.mitmproxy import tutils


class Dummy:
    def __init__(self, reply):
        self.reply = reply


@tutils.skip_appveyor
def test_concurrent():
    with Script(tutils.test_data.path("scripts/concurrent_decorator.py"), None) as s:
        def reply():
            reply.acked.set()
        reply.acked = Event()

        f1, f2 = Dummy(reply), Dummy(reply)
        s.run("request", f1)
        f1.reply()
        s.run("request", f2)
        f2.reply()
        assert f1.reply.acked == reply.acked
        assert not reply.acked.is_set()
        assert reply.acked.wait(10)


def test_concurrent_err():
    s = Script(tutils.test_data.path("scripts/concurrent_decorator_err.py"), None)
    with tutils.raises("Concurrent decorator not supported for 'start' method"):
        s.load()
