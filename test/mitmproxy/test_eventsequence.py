from mitmproxy import events
import contextlib
from . import tservers


class Eventer:
    def __init__(self, **handlers):
        self.failure = None
        self.called = []
        self.handlers = handlers
        for i in events.Events - {"tick"}:
            def mkprox():
                evt = i

                def prox(*args, **kwargs):
                    self.called.append(evt)
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
    def addon(self, addon):
        self.master.addons.add(addon)
        yield
        self.master.addons.remove(addon)
        if addon.failure:
            raise addon.failure


class TestBasic(tservers.HTTPProxyTest, SequenceTester):
    ssl = True

    def test_requestheaders(self):

        def hdrs(f):
            assert f.request.headers
            assert not f.request.content

        def req(f):
            assert f.request.headers
            assert f.request.content

        with self.addon(Eventer(requestheaders=hdrs, request=req)):
            p = self.pathoc()
            with p.connect():
                assert p.request("get:'/p/200':b@10").status_code == 200

    def test_100_continue_fail(self):
        e = Eventer()
        with self.addon(e):
            p = self.pathoc()
            with p.connect():
                p.request(
                    """
                        get:'/p/200'
                        h'expect'='100-continue'
                        h'content-length'='1000'
                        da
                    """
                )
        assert "requestheaders" in e.called
        assert "responseheaders" not in e.called

    def test_connect(self):
        e = Eventer()
        with self.addon(e):
            p = self.pathoc()
            with p.connect():
                p.request("get:'/p/200:b@1'")
            assert "http_connect" in e.called
            assert e.called.count("requestheaders") == 1
            assert e.called.count("request") == 1
