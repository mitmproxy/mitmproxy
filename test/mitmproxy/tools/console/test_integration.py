def test_integration(tdata, console):
    console.type(
        f":view.flows.load {tdata.path('mitmproxy/data/dumpfile-7.mitm')}<enter>"
    )
    console.type("<enter><tab><tab>")
    console.type("<space><tab><tab>")  # view second flow
    assert "http://example.com/" in console.screen_contents()


def test_load_compressed_zstd(tmp_path, console):
    import zstandard as zstd

    from mitmproxy import io as mio
    from mitmproxy.test import tflow

    p = tmp_path / "flows.zst"
    cctx = zstd.ZstdCompressor()
    with open(str(p), "wb") as raw:
        with cctx.stream_writer(raw) as writer:
            w = mio.FlowWriter(writer)
            flow = tflow.tflow(resp=True)
            flow.request.url = "http://compressed.example.com/zstdtest"
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
