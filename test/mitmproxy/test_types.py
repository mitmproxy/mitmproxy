import pytest
import os
import typing
import contextlib

import mitmproxy.exceptions
import mitmproxy.types
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy import command
from mitmproxy import flow

from . import test_command


@contextlib.contextmanager
def chdir(path: str):
    old_dir = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_dir)


def test_bool():
    with taddons.context() as tctx:
        b = mitmproxy.types._BoolType()
        assert b.completion(tctx.master.commands, bool, "b") == ["false", "true"]
        assert b.parse(tctx.master.commands, bool, "true") is True
        assert b.parse(tctx.master.commands, bool, "false") is False
        assert b.is_valid(tctx.master.commands, bool, True) is True
        assert b.is_valid(tctx.master.commands, bool, "foo") is False
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, bool, "foo")


def test_str():
    with taddons.context() as tctx:
        b = mitmproxy.types._StrType()
        assert b.is_valid(tctx.master.commands, str, "foo") is True
        assert b.is_valid(tctx.master.commands, str, 1) is False
        assert b.completion(tctx.master.commands, str, "") == []
        assert b.parse(tctx.master.commands, str, "foo") == "foo"
        assert b.parse(tctx.master.commands, str, r"foo\nbar") == "foo\nbar"
        assert b.parse(tctx.master.commands, str, r"\N{BELL}") == "🔔"
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, bool, r"\N{UNKNOWN UNICODE SYMBOL!}")


def test_bytes():
    with taddons.context() as tctx:
        b = mitmproxy.types._BytesType()
        assert b.is_valid(tctx.master.commands, bytes, b"foo") is True
        assert b.is_valid(tctx.master.commands, bytes, 1) is False
        assert b.completion(tctx.master.commands, bytes, "") == []
        assert b.parse(tctx.master.commands, bytes, "foo") == b"foo"
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, bytes, "incomplete escape sequence\\")


def test_unknown():
    with taddons.context() as tctx:
        b = mitmproxy.types._UnknownType()
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Unknown, "foo") is False
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Unknown, 1) is False
        assert b.completion(tctx.master.commands, mitmproxy.types.Unknown, "") == []
        assert b.parse(tctx.master.commands, mitmproxy.types.Unknown, "foo") == "foo"


def test_int():
    with taddons.context() as tctx:
        b = mitmproxy.types._IntType()
        assert b.is_valid(tctx.master.commands, int, "foo") is False
        assert b.is_valid(tctx.master.commands, int, 1) is True
        assert b.completion(tctx.master.commands, int, "b") == []
        assert b.parse(tctx.master.commands, int, "1") == 1
        assert b.parse(tctx.master.commands, int, "999") == 999
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, int, "foo")


def test_path(tdata, monkeypatch):
    with taddons.context() as tctx:
        b = mitmproxy.types._PathType()
        assert b.parse(tctx.master.commands, mitmproxy.types.Path, "/foo") == "/foo"
        assert b.parse(tctx.master.commands, mitmproxy.types.Path, "/bar") == "/bar"
        monkeypatch.setenv("HOME", "/home/test")
        monkeypatch.setenv("USERPROFILE", "/home/test")
        assert b.parse(tctx.master.commands, mitmproxy.types.Path, "~/mitm") == "/home/test/mitm"
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Path, "foo") is True
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Path, "~/mitm") is True
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Path, 3) is False

        def normPathOpts(prefix, match):
            ret = []
            for s in b.completion(tctx.master.commands, mitmproxy.types.Path, match):
                s = s[len(prefix):]
                s = s.replace(os.sep, "/")
                ret.append(s)
            return ret

        cd = os.path.normpath(tdata.path("mitmproxy/completion"))
        assert normPathOpts(cd, cd) == ['/aaa', '/aab', '/aac', '/bbb/']
        assert normPathOpts(cd, os.path.join(cd, "a")) == ['/aaa', '/aab', '/aac']
        with chdir(cd):
            assert normPathOpts("", "./") == ['./aaa', './aab', './aac', './bbb/']
            assert normPathOpts("", "") == ['./aaa', './aab', './aac', './bbb/']
        assert b.completion(
            tctx.master.commands, mitmproxy.types.Path, "nonexistent"
        ) == ["nonexistent"]


def test_cmd():
    with taddons.context() as tctx:
        tctx.master.addons.add(test_command.TAddon())
        b = mitmproxy.types._CmdType()
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Cmd, "foo") is False
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Cmd, "cmd1") is True
        assert b.parse(tctx.master.commands, mitmproxy.types.Cmd, "cmd1") == "cmd1"
        with pytest.raises(mitmproxy.exceptions.TypeError):
            assert b.parse(tctx.master.commands, mitmproxy.types.Cmd, "foo")
        assert len(
            b.completion(tctx.master.commands, mitmproxy.types.Cmd, "")
        ) == len(tctx.master.commands.commands.keys())


def test_cutspec():
    with taddons.context() as tctx:
        b = mitmproxy.types._CutSpecType()
        b.parse(tctx.master.commands, mitmproxy.types.CutSpec, "foo,bar") == ["foo", "bar"]
        assert b.is_valid(tctx.master.commands, mitmproxy.types.CutSpec, 1) is False
        assert b.is_valid(tctx.master.commands, mitmproxy.types.CutSpec, "foo") is False
        assert b.is_valid(tctx.master.commands, mitmproxy.types.CutSpec, "request.path") is True

        assert b.completion(
            tctx.master.commands, mitmproxy.types.CutSpec, "request.p"
        ) == b.valid_prefixes
        ret = b.completion(tctx.master.commands, mitmproxy.types.CutSpec, "request.port,f")
        assert ret[0].startswith("request.port,")
        assert len(ret) == len(b.valid_prefixes)


def test_marker():
    with taddons.context() as tctx:
        b = mitmproxy.types._MarkerType()
        assert b.parse(tctx.master.commands, mitmproxy.types.Marker, ":red_circle:") == ":red_circle:"
        assert b.parse(tctx.master.commands, mitmproxy.types.Marker, "true") == ":default:"
        assert b.parse(tctx.master.commands, mitmproxy.types.Marker, "false") == ""

        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, mitmproxy.types.Marker, ":bogus:")

        assert b.is_valid(tctx.master.commands, mitmproxy.types.Marker, "true") is True
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Marker, "false") is True
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Marker, "bogus") is False
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Marker, "X") is True
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Marker, ":red_circle:") is True
        ret = b.completion(tctx.master.commands, mitmproxy.types.Marker, ":smil")
        assert len(ret) > 10


def test_arg():
    with taddons.context() as tctx:
        b = mitmproxy.types._ArgType()
        assert b.completion(tctx.master.commands, mitmproxy.types.CmdArgs, "") == []
        assert b.parse(tctx.master.commands, mitmproxy.types.CmdArgs, "foo") == "foo"
        assert b.is_valid(tctx.master.commands, mitmproxy.types.CmdArgs, 1) is False


def test_strseq():
    with taddons.context() as tctx:
        b = mitmproxy.types._StrSeqType()
        assert b.completion(tctx.master.commands, typing.Sequence[str], "") == []
        assert b.parse(tctx.master.commands, typing.Sequence[str], "foo") == ["foo"]
        assert b.parse(tctx.master.commands, typing.Sequence[str], "foo,bar") == ["foo", "bar"]
        assert b.is_valid(tctx.master.commands, typing.Sequence[str], ["foo"]) is True
        assert b.is_valid(tctx.master.commands, typing.Sequence[str], ["a", "b", 3]) is False
        assert b.is_valid(tctx.master.commands, typing.Sequence[str], 1) is False
        assert b.is_valid(tctx.master.commands, typing.Sequence[str], "foo") is False


class DummyConsole:
    @command.command("view.flows.resolve")
    def resolve(self, spec: str) -> typing.Sequence[flow.Flow]:
        if spec == "err":
            raise mitmproxy.exceptions.CommandError()
        n = int(spec)
        return [tflow.tflow(resp=True)] * n

    @command.command("cut")
    def cut(self, spec: str) -> mitmproxy.types.Data:
        return [["test"]]

    @command.command("options")
    def options(self) -> typing.Sequence[str]:
        return ["one", "two", "three"]


def test_flow():
    with taddons.context() as tctx:
        tctx.master.addons.add(DummyConsole())
        b = mitmproxy.types._FlowType()
        assert len(b.completion(tctx.master.commands, flow.Flow, "")) == len(b.valid_prefixes)
        assert b.parse(tctx.master.commands, flow.Flow, "1")
        assert b.is_valid(tctx.master.commands, flow.Flow, tflow.tflow()) is True
        assert b.is_valid(tctx.master.commands, flow.Flow, "xx") is False
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, flow.Flow, "0")
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, flow.Flow, "2")
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, flow.Flow, "err")


def test_flows():
    with taddons.context() as tctx:
        tctx.master.addons.add(DummyConsole())
        b = mitmproxy.types._FlowsType()
        assert len(
            b.completion(tctx.master.commands, typing.Sequence[flow.Flow], "")
        ) == len(b.valid_prefixes)
        assert b.is_valid(tctx.master.commands, typing.Sequence[flow.Flow], [tflow.tflow()]) is True
        assert b.is_valid(tctx.master.commands, typing.Sequence[flow.Flow], "xx") is False
        assert b.is_valid(tctx.master.commands, typing.Sequence[flow.Flow], 0) is False
        assert len(b.parse(tctx.master.commands, typing.Sequence[flow.Flow], "0")) == 0
        assert len(b.parse(tctx.master.commands, typing.Sequence[flow.Flow], "1")) == 1
        assert len(b.parse(tctx.master.commands, typing.Sequence[flow.Flow], "2")) == 2
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, typing.Sequence[flow.Flow], "err")


def test_data():
    with taddons.context() as tctx:
        b = mitmproxy.types._DataType()
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Data, 0) is False
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Data, []) is True
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Data, [["x"]]) is True
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Data, [[b"x"]]) is True
        assert b.is_valid(tctx.master.commands, mitmproxy.types.Data, [[1]]) is False
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, mitmproxy.types.Data, "foo")
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, mitmproxy.types.Data, "foo")


def test_choice():
    with taddons.context() as tctx:
        tctx.master.addons.add(DummyConsole())
        b = mitmproxy.types._ChoiceType()
        assert b.is_valid(
            tctx.master.commands,
            mitmproxy.types.Choice("options"),
            "one",
        ) is True
        assert b.is_valid(
            tctx.master.commands,
            mitmproxy.types.Choice("options"),
            "invalid",
        ) is False
        assert b.is_valid(
            tctx.master.commands,
            mitmproxy.types.Choice("nonexistent"),
            "invalid",
        ) is False
        comp = b.completion(tctx.master.commands, mitmproxy.types.Choice("options"), "")
        assert comp == ["one", "two", "three"]
        assert b.parse(tctx.master.commands, mitmproxy.types.Choice("options"), "one") == "one"
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, mitmproxy.types.Choice("options"), "invalid")


def test_typemanager():
    assert mitmproxy.types.CommandTypes.get(bool, None)
    assert mitmproxy.types.CommandTypes.get(mitmproxy.types.Choice("choide"), None)
