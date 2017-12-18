import pytest
import os
import typing
import contextlib

from mitmproxy.test import tutils
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
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, bool, "foo")


def test_str():
    with taddons.context() as tctx:
        b = mitmproxy.types._StrType()
        assert b.completion(tctx.master.commands, str, "") == []
        assert b.parse(tctx.master.commands, str, "foo") == "foo"


def test_int():
    with taddons.context() as tctx:
        b = mitmproxy.types._IntType()
        assert b.completion(tctx.master.commands, int, "b") == []
        assert b.parse(tctx.master.commands, int, "1") == 1
        assert b.parse(tctx.master.commands, int, "999") == 999
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, int, "foo")


def test_path():
    with taddons.context() as tctx:
        b = mitmproxy.types._PathType()
        assert b.parse(tctx.master.commands, mitmproxy.types.Path, "/foo") == "/foo"
        assert b.parse(tctx.master.commands, mitmproxy.types.Path, "/bar") == "/bar"

        def normPathOpts(prefix, match):
            ret = []
            for s in b.completion(tctx.master.commands, mitmproxy.types.Path, match):
                s = s[len(prefix):]
                s = s.replace(os.sep, "/")
                ret.append(s)
            return ret

        cd = os.path.normpath(tutils.test_data.path("mitmproxy/completion"))
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
        assert b.parse(tctx.master.commands, mitmproxy.types.Cmd, "foo") == "foo"
        assert len(
            b.completion(tctx.master.commands, mitmproxy.types.Cmd, "")
        ) == len(tctx.master.commands.commands.keys())


def test_cutspec():
    with taddons.context() as tctx:
        b = mitmproxy.types._CutSpecType()
        b.parse(tctx.master.commands, mitmproxy.types.CutSpec, "foo,bar") == ["foo", "bar"]
        assert b.completion(
            tctx.master.commands, mitmproxy.types.CutSpec, "request.p"
        ) == b.valid_prefixes
        ret = b.completion(tctx.master.commands, mitmproxy.types.CutSpec, "request.port,f")
        assert ret[0].startswith("request.port,")
        assert len(ret) == len(b.valid_prefixes)


def test_arg():
    with taddons.context() as tctx:
        b = mitmproxy.types._ArgType()
        assert b.completion(tctx.master.commands, mitmproxy.types.Arg, "") == []
        assert b.parse(tctx.master.commands, mitmproxy.types.Arg, "foo") == "foo"


def test_strseq():
    with taddons.context() as tctx:
        b = mitmproxy.types._StrSeqType()
        assert b.completion(tctx.master.commands, typing.Sequence[str], "") == []
        assert b.parse(tctx.master.commands, typing.Sequence[str], "foo") == ["foo"]
        assert b.parse(tctx.master.commands, typing.Sequence[str], "foo,bar") == ["foo", "bar"]


class DummyConsole:
    @command.command("view.resolve")
    def resolve(self, spec: str) -> typing.Sequence[flow.Flow]:
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
        with pytest.raises(mitmproxy.exceptions.TypeError):
            assert b.parse(tctx.master.commands, flow.Flow, "0")
        with pytest.raises(mitmproxy.exceptions.TypeError):
            assert b.parse(tctx.master.commands, flow.Flow, "2")


def test_flows():
    with taddons.context() as tctx:
        tctx.master.addons.add(DummyConsole())
        b = mitmproxy.types._FlowsType()
        assert len(
            b.completion(tctx.master.commands, typing.Sequence[flow.Flow], "")
        ) == len(b.valid_prefixes)
        assert len(b.parse(tctx.master.commands, typing.Sequence[flow.Flow], "0")) == 0
        assert len(b.parse(tctx.master.commands, typing.Sequence[flow.Flow], "1")) == 1
        assert len(b.parse(tctx.master.commands, typing.Sequence[flow.Flow], "2")) == 2


def test_data():
    with taddons.context() as tctx:
        b = mitmproxy.types._DataType()
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, mitmproxy.types.Data, "foo")
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, mitmproxy.types.Data, "foo")


def test_choice():
    with taddons.context() as tctx:
        tctx.master.addons.add(DummyConsole())
        b = mitmproxy.types._ChoiceType()
        comp = b.completion(tctx.master.commands, mitmproxy.types.Choice("options"), "")
        assert comp == ["one", "two", "three"]
        assert b.parse(tctx.master.commands, mitmproxy.types.Choice("options"), "one") == "one"
        with pytest.raises(mitmproxy.exceptions.TypeError):
            b.parse(tctx.master.commands, mitmproxy.types.Choice("options"), "invalid")


def test_typemanager():
    assert mitmproxy.types.CommandTypes.get(bool, None)
    assert mitmproxy.types.CommandTypes.get(mitmproxy.types.Choice("choide"), None)
