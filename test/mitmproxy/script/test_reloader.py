import mock
from mitmproxy.script.reloader import watch, unwatch
from test.mitmproxy import tutils
from threading import Event


def test_simple():
    with tutils.tmpdir():
        with open("foo.py", "wb"):
            pass

        script = mock.Mock()
        script.filename = "foo.py"

        e = Event()

        def _onchange():
            e.set()

        watch(script, _onchange)
        with tutils.raises("already observed"):
            watch(script, _onchange)

        with open("foo.py", "ab") as f:
            f.write(".")

        assert e.wait(10)

        unwatch(script)
