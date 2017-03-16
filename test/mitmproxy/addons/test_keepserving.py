from mitmproxy.addons import keepserving
from mitmproxy.test import taddons


def test_keepserving():
    ks = keepserving.KeepServing()

    with taddons.context() as tctx:
        ks.event_processing_complete()
        assert tctx.master.should_exit.is_set()
