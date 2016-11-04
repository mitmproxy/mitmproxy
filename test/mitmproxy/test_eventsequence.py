from mitmproxy import events
import contextlib
from . import tservers


class EAddon:
    def __init__(self, handlers):
        self.failure = None
        self.handlers = handlers
        for i in events.Events:
            def mkprox():
                evt = i

                def prox(*args, **kwargs):
                    if evt in self.handlers:
                        try:
                            handlers[evt](*args, **kwargs)
                        except AssertionError as e:
                            self.failure = e
                return prox
            setattr(self, i, mkprox())

    def fail(self):
        pass


class SequenceTester:
    @contextlib.contextmanager
    def events(self, **kwargs):
        m = EAddon(kwargs)
        self.master.addons.add(m)
        yield
        self.master.addons.remove(m)
        if m.failure:
            raise m.failure


class TestBasic(tservers.HTTPProxyTest, SequenceTester):
    def test_requestheaders(self):

        def req(f):
            assert f.request.headers
            assert not f.request.content

        with self.events(requestheaders=req):
            p = self.pathoc()
            with p.connect():
                assert p.request("get:'%s/p/200':b@10" % self.server.urlbase).status_code == 200
