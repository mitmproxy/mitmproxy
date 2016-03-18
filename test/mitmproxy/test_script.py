from mitmproxy import flow
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
