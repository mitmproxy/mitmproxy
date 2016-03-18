import time
import mock
from mitmproxy import script, flow
from . import tutils


def test_duplicate_flow():
    s = flow.State()
    fm = flow.FlowMaster(None, s)
    fm.load_script(tutils.test_data.path("scripts/duplicate_flow.py"))
    f = tutils.tflow()
    fm.handle_request(f)
    assert fm.state.flow_count() == 2
    assert not fm.state.view[0].request.is_replay
    assert fm.state.view[1].request.is_replay


@tutils.skip_appveyor
def test_concurrent():
    s = flow.State()
    fm = flow.FlowMaster(None, s)
    fm.load_script(tutils.test_data.path("scripts/concurrent_decorator.py"))

    with mock.patch("mitmproxy.controller.DummyReply.__call__") as m:
        f1, f2 = tutils.tflow(), tutils.tflow()
        t_start = time.time()
        fm.handle_request(f1)
        f1.reply()
        fm.handle_request(f2)
        f2.reply()

        # Two instantiations
        assert m.call_count == 0  # No calls yet.
        assert (time.time() - t_start) < 0.1


def test_concurrent2():
    s = flow.State()
    fm = flow.FlowMaster(None, s)
    s = script.Script(
        tutils.test_data.path("scripts/concurrent_decorator.py"),
        script.ScriptContext(fm))
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
    with tutils.raises("Concurrent decorator not supported for 'start' method"):
        s = script.Script(tutils.test_data.path("scripts/concurrent_decorator_err.py"), fm)
        s.load()