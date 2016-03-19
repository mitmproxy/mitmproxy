import mock
from mitmproxy.script.reloader import watch, unwatch
from test.mitmproxy import tutils
from threading import Event


def test_simple():
    with tutils.tmpdir():
        with open("foo.py", "w"):
            pass

        script = mock.Mock()
        script.filename = "foo.py"

        e = Event()

        def _onchange():
            e.set()

        watch(script, _onchange)
        with tutils.raises("already observed"):
            watch(script, _onchange)

        # Some reloaders don't register a change directly after watching, because they first need to initialize.
        # To test if watching works at all, we do repeated writes every 100ms.
        for _ in range(100):
            with open("foo.py", "a") as f:
                f.write(".")
            if e.wait(0.1):
                break
        else:
            raise AssertionError("No change detected.")

        unwatch(script)
