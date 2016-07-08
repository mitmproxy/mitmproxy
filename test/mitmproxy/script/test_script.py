from mitmproxy.script import Script
from mitmproxy.exceptions import ScriptException
from test.mitmproxy import tutils


class TestParseCommand:
    def test_empty_command(self):
        with tutils.raises(ScriptException):
            Script.parse_command("")

        with tutils.raises(ScriptException):
            Script.parse_command("  ")

    def test_no_script_file(self):
        with tutils.raises("not found"):
            Script.parse_command("notfound")

        with tutils.tmpdir() as dir:
            with tutils.raises("not a file"):
                Script.parse_command(dir)

    def test_parse_args(self):
        with tutils.chdir(tutils.test_data.dirname):
            assert Script.parse_command("data/scripts/a.py") == ("data/scripts/a.py", [])
            assert Script.parse_command("data/scripts/a.py foo bar") == ("data/scripts/a.py", ["foo", "bar"])
            assert Script.parse_command("data/scripts/a.py 'foo bar'") == ("data/scripts/a.py", ["foo bar"])

    @tutils.skip_not_windows
    def test_parse_windows(self):
        with tutils.chdir(tutils.test_data.dirname):
            assert Script.parse_command("data\\scripts\\a.py") == ("data\\scripts\\a.py", [])
            assert Script.parse_command("data\\scripts\\a.py 'foo \\ bar'") == ("data\\scripts\\a.py", ['foo \\ bar'])


def test_simple():
    with tutils.chdir(tutils.test_data.path("data/scripts")):
        s = Script("a.py --var 42")
        assert s.path == "a.py"
        assert s.ns is None

        s.load()
        assert s.ns["var"] == 42

        s.run("here")
        assert s.ns["var"] == 43

        s.unload()
        assert s.ns is None

        with tutils.raises(ScriptException):
            s.run("here")

        with Script("a.py --var 42") as s:
            s.run("here")


def test_script_exception():
    with tutils.chdir(tutils.test_data.path("data/scripts")):
        s = Script("syntaxerr.py")
        with tutils.raises(ScriptException):
            s.load()

        s = Script("starterr.py")
        with tutils.raises(ScriptException):
            s.load()

        s = Script("a.py")
        s.load()
        with tutils.raises(ScriptException):
            s.load()

        s = Script("a.py")
        with tutils.raises(ScriptException):
            s.run("here")

        with tutils.raises(ScriptException):
            with Script("reqerr.py") as s:
                s.run("request", None)

        s = Script("unloaderr.py")
        s.load()
        with tutils.raises(ScriptException):
            s.unload()
