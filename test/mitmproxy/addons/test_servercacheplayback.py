import os
from mitmproxy.test import tutils
from mitmproxy.test import tflow
from mitmproxy.test import taddons

from mitmproxy.addons import servercacheplayback
from mitmproxy import options
from mitmproxy import exceptions
from mitmproxy import io


def tdump(path, flows):
    w = io.FlowWriter(open(path, "wb"))
    for i in flows:
        w.add(i)


def test_config():
    s = servercacheplayback.ServerCachePlayBack()
    with tutils.tmpdir() as p:
        with taddons.context() as tctx:
            fpath = os.path.join(p, "flows")
            flow = tflow.tflow(resp=True)

            assert not flow.response.is_replay

            tdump(fpath, [tflow.tflow(resp=True)])
            tctx.configure(s, server_cache_replay=True, server_cache_replay_load=[fpath])

            # Make sure the response is now a replay
            s.request(flow)

            assert flow.response.is_replay


def test_config_invalid_file():
    s = servercacheplayback.ServerCachePlayBack()
    with tutils.tmpdir() as p:
        with taddons.context() as tctx:
            fpath = os.path.join(p, "flows")
            tdump(fpath, [tflow.tflow(resp=True)])
            tutils.raises(exceptions.OptionsError, tctx.configure, s,
                          server_cache_replay=True,
                          server_cache_replay_load=[p])


def test_tick():
    s = servercacheplayback.ServerCachePlayBack()
    with taddons.context() as tctx:
        s.stop = True
        s.final_flow = tflow.tflow()
        s.final_flow.live = False
        s.tick()
        assert tctx.master.should_exit.is_set()


def test_server_cache_playback():
    scp = servercacheplayback.ServerCachePlayBack()
    scp.configure(options.Options(), [])
    f = tflow.tflow(resp=True)

    assert not scp.enabled
    assert not scp.flowmap

    scp.enable(flows=[f])

    assert scp.enabled
    assert scp.flowmap

    scp.request(f)
    assert f.response.is_replay


def test_server_cache_playback_disabled_no_response():
    scp = servercacheplayback.ServerCachePlayBack()
    scp.configure(options.Options(), [])
    f = tflow.tflow(resp=True)

    assert not scp.enabled
    assert not scp.flowmap

    scp.request(f)
    assert not f.response.is_replay
