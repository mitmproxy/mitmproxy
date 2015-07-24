import os
import time
import mock
from libmproxy import script, flow
import tutils


def test_simple():
    s = flow.State()
    fm = flow.FlowMaster(None, s)
    sp = tutils.test_data.path("scripts/a.py")
    p = script.Script("%s --var 40" % sp, fm)

    assert "here" in p.ns
    assert p.run("here") == 41
    assert p.run("here") == 42

    tutils.raises(script.ScriptError, p.run, "errargs")

    # Check reload
    p.load()
    assert p.run("here") == 41


def test_duplicate_flow():
    s = flow.State()
    fm = flow.FlowMaster(None, s)
    fm.load_script(tutils.test_data.path("scripts/duplicate_flow.py"))
    f = tutils.tflow()
    fm.handle_request(f)
    assert fm.state.flow_count() == 2
    assert not fm.state.view[0].request.is_replay
    assert fm.state.view[1].request.is_replay


def test_err():
    s = flow.State()
    fm = flow.FlowMaster(None, s)

    tutils.raises(
        "not found",
        script.Script, "nonexistent", fm
    )

    tutils.raises(
        "not a file",
        script.Script, tutils.test_data.path("scripts"), fm
    )

    tutils.raises(
        script.ScriptError,
        script.Script, tutils.test_data.path("scripts/syntaxerr.py"), fm
    )

    tutils.raises(
        script.ScriptError,
        script.Script, tutils.test_data.path("scripts/loaderr.py"), fm
    )

    scr = script.Script(tutils.test_data.path("scripts/unloaderr.py"), fm)
    tutils.raises(script.ScriptError, scr.unload)


def test_concurrent():
    s = flow.State()
    fm = flow.FlowMaster(None, s)
    fm.load_script(tutils.test_data.path("scripts/concurrent_decorator.py"))

    with mock.patch("libmproxy.controller.DummyReply.__call__") as m:
        f1, f2 = tutils.tflow(), tutils.tflow()
        t_start = time.time()
        fm.handle_request(f1)
        f1.reply()
        fm.handle_request(f2)
        f2.reply()

        # Two instantiations
        assert m.call_count == 0  # No calls yet.
        assert (time.time() - t_start) < 0.09


def test_concurrent2():
    s = flow.State()
    fm = flow.FlowMaster(None, s)
    s = script.Script(
        tutils.test_data.path("scripts/concurrent_decorator.py"),
        fm)
    s.load()
    m = mock.Mock()

    class Dummy:
        def __init__(self):
            self.response = self
            self.error = self
            self.reply = m

    t_start = time.time()

    for hook in ("clientconnect",
                 "serverconnect",
                 "response",
                 "error",
                 "clientconnect"):
        d = Dummy()
        s.run(hook, d)
        d.reply()
    while (time.time() - t_start) < 20 and m.call_count <= 5:
        if m.call_count == 5:
            return
        time.sleep(0.001)
    assert False


def test_concurrent_err():
    s = flow.State()
    fm = flow.FlowMaster(None, s)
    tutils.raises(
        "Concurrent decorator not supported for 'start' method",
        script.Script,
        tutils.test_data.path("scripts/concurrent_decorator_err.py"),
        fm)


def test_command_parsing():
    s = flow.State()
    fm = flow.FlowMaster(None, s)
    absfilepath = os.path.normcase(tutils.test_data.path("scripts/a.py"))
    s = script.Script(absfilepath, fm)
    assert os.path.isfile(s.args[0])
