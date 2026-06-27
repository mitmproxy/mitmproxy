def test_integration(tdata, console):
    console.type(
        f":view.flows.load {tdata.path('mitmproxy/data/dumpfile-7.mitm')}<enter>"
    )
    console.type("<enter><tab><tab>")
    console.type("<space><tab><tab>")  # view second flow
    assert "http://example.com/" in console.screen_contents()


def test_load_compressed_gzip(tmp_path, console):
    import gzip

    from mitmproxy import io as mio
    from mitmproxy.test import tflow

    p = tmp_path / "flows.gz"
    with gzip.open(str(p), "wb") as f:
        w = mio.FlowWriter(f)
        flow = tflow.tflow(resp=True)
        flow.request.url = "http://compressed.example.com/gztest"
        w.add(flow)

    console.type(f":view.flows.load {p}<enter>")
    assert "compressed.example.com" in console.screen_contents()


def test_load_compressed_bz2(tmp_path, console):
    import bz2

    from mitmproxy import io as mio
    from mitmproxy.test import tflow

    p = tmp_path / "flows.bz2"
    with bz2.open(str(p), "wb") as f:
        w = mio.FlowWriter(f)
        flow = tflow.tflow(resp=True)
        flow.request.url = "http://compressed.example.com/bz2test"
        w.add(flow)

    console.type(f":view.flows.load {p}<enter>")
    assert "compressed.example.com" in console.screen_contents()


def test_load_compressed_xz(tmp_path, console):
    import lzma

    from mitmproxy import io as mio
    from mitmproxy.test import tflow

    p = tmp_path / "flows.xz"
    with lzma.open(str(p), "wb") as f:
        w = mio.FlowWriter(f)
        flow = tflow.tflow(resp=True)
        flow.request.url = "http://compressed.example.com/xztest"
        w.add(flow)

    console.type(f":view.flows.load {p}<enter>")
    assert "compressed.example.com" in console.screen_contents()


def test_options_home_end(console):
    console.type("O<home><end>")
    assert "Options" in console.screen_contents()


def test_keybindings_home_end(console):
    console.type("K<home><end>")
    assert "Key Binding" in console.screen_contents()


def test_replay_count(console):
    console.type(":replay.server.count<enter>")
    assert "Data viewer" in console.screen_contents()
