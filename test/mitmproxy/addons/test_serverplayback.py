import urllib
from types import SimpleNamespace

import pytest

import mitmproxy.test.tutils
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import http
from mitmproxy import io
from mitmproxy.addons import serverplayback
from mitmproxy.test import taddons
from mitmproxy.test import tflow


def tdump(path, flows):
    with open(path, "wb") as f:
        w = io.FlowWriter(f)
        for i in flows:
            w.add(i)


def test_load_file(tmpdir):
    s = serverplayback.ServerPlayback()
    with taddons.context(s):
        fpath = str(tmpdir.join("flows"))
        tdump(fpath, [tflow.tflow(resp=True)])
        s.load_file(fpath)
        assert s.flowmap
        with pytest.raises(exceptions.CommandError):
            s.load_file("/nonexistent")


def test_config(tmpdir):
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        fpath = str(tmpdir.join("flows"))
        tdump(fpath, [tflow.tflow(resp=True)])
        tctx.configure(s, server_replay=[fpath])
        s.configured = False
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(s, server_replay=[str(tmpdir)])


def test_server_playback():
    sp = serverplayback.ServerPlayback()
    with taddons.context(sp) as tctx:
        tctx.configure(sp)
        f = tflow.tflow(resp=True)

        assert not sp.flowmap

        sp.load_flows([f])
        assert sp.flowmap
        assert sp.next_flow(f)
        assert not sp.flowmap

        sp.load_flows([f])
        assert sp.flowmap
        sp.clear()
        assert not sp.flowmap


def test_add_flows():
    sp = serverplayback.ServerPlayback()
    with taddons.context(sp) as tctx:
        tctx.configure(sp)
        f1 = tflow.tflow(resp=True)
        f2 = tflow.tflow(resp=True)

        sp.load_flows([f1])
        sp.add_flows([f2])

        assert sp.next_flow(f1)
        assert sp.flowmap
        assert sp.next_flow(f2)
        assert not sp.flowmap

        sp.add_flows([f1])
        assert sp.flowmap
        assert sp.next_flow(f1)
        assert not sp.flowmap


def test_ignore_host():
    sp = serverplayback.ServerPlayback()
    with taddons.context(sp) as tctx:
        tctx.configure(sp, server_replay_ignore_host=True)

        r = tflow.tflow(resp=True)
        r2 = tflow.tflow(resp=True)

        r.request.host = "address"
        r2.request.host = "address"
        assert sp._hash(r) == sp._hash(r2)
        r2.request.host = "wrong_address"
        assert sp._hash(r) == sp._hash(r2)


def test_ignore_content():
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        tctx.configure(s, server_replay_ignore_content=False)

        r = tflow.tflow(resp=True)
        r2 = tflow.tflow(resp=True)

        r.request.content = b"foo"
        r2.request.content = b"foo"
        assert s._hash(r) == s._hash(r2)
        r2.request.content = b"bar"
        assert not s._hash(r) == s._hash(r2)

        tctx.configure(s, server_replay_ignore_content=True)
        r = tflow.tflow(resp=True)
        r2 = tflow.tflow(resp=True)
        r.request.content = b"foo"
        r2.request.content = b"foo"
        assert s._hash(r) == s._hash(r2)
        r2.request.content = b"bar"
        assert s._hash(r) == s._hash(r2)
        r2.request.content = b""
        assert s._hash(r) == s._hash(r2)
        r2.request.content = None
        assert s._hash(r) == s._hash(r2)


def test_ignore_content_wins_over_params():
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        tctx.configure(
            s,
            server_replay_ignore_content=True,
            server_replay_ignore_payload_params=["param1", "param2"],
        )

        # NOTE: parameters are mutually exclusive in options
        r = tflow.tflow(resp=True)
        r.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        r.request.content = b"paramx=y"

        r2 = tflow.tflow(resp=True)
        r2.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        r2.request.content = b"paramx=x"

        # same parameters
        assert s._hash(r) == s._hash(r2)


def test_ignore_payload_params_other_content_type():
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        tctx.configure(
            s,
            server_replay_ignore_content=False,
            server_replay_ignore_payload_params=["param1", "param2"],
        )

        r = tflow.tflow(resp=True)
        r.request.headers["Content-Type"] = "application/json"
        r.request.content = b'{"param1":"1"}'
        r2 = tflow.tflow(resp=True)
        r2.request.headers["Content-Type"] = "application/json"
        r2.request.content = b'{"param1":"1"}'
        # same content
        assert s._hash(r) == s._hash(r2)
        # distinct content (note only x-www-form-urlencoded payload is analysed)
        r2.request.content = b'{"param1":"2"}'
        assert not s._hash(r) == s._hash(r2)


def test_hash():
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        tctx.configure(s)

        r = tflow.tflow()
        r2 = tflow.tflow()

        assert s._hash(r)
        assert s._hash(r) == s._hash(r2)
        r.request.headers["foo"] = "bar"
        assert s._hash(r) == s._hash(r2)
        r.request.path = "voing"
        assert s._hash(r) != s._hash(r2)

        r.request.path = "path?blank_value"
        r2.request.path = "path?"
        assert s._hash(r) != s._hash(r2)


def test_headers():
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        tctx.configure(s, server_replay_use_headers=["foo"])

        r = tflow.tflow(resp=True)
        r.request.headers["foo"] = "bar"
        r2 = tflow.tflow(resp=True)
        assert not s._hash(r) == s._hash(r2)
        r2.request.headers["foo"] = "bar"
        assert s._hash(r) == s._hash(r2)
        r2.request.headers["oink"] = "bar"
        assert s._hash(r) == s._hash(r2)

        r = tflow.tflow(resp=True)
        r2 = tflow.tflow(resp=True)
        assert s._hash(r) == s._hash(r2)


def test_load():
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        tctx.configure(s)

        r = tflow.tflow(resp=True)
        r.request.headers["key"] = "one"

        r2 = tflow.tflow(resp=True)
        r2.request.headers["key"] = "two"

        s.load_flows([r, r2])

        assert s.count() == 2

        n = s.next_flow(r)
        assert n.request.headers["key"] == "one"
        assert s.count() == 1

        n = s.next_flow(r)
        assert n.request.headers["key"] == "two"
        assert not s.flowmap
        assert s.count() == 0

        assert not s.next_flow(r)


def test_load_with_server_replay_reuse():
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        tctx.configure(s, server_replay_reuse=True)

        r = tflow.tflow(resp=True)
        r.request.headers["key"] = "one"

        r2 = tflow.tflow(resp=True)
        r2.request.headers["key"] = "two"

        s.load_flows([r, r2])

        assert s.count() == 2
        s.next_flow(r)
        assert s.count() == 2


def test_ignore_params():
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        tctx.configure(s, server_replay_ignore_params=["param1", "param2"])

        r = tflow.tflow(resp=True)
        r.request.path = "/test?param1=1"
        r2 = tflow.tflow(resp=True)
        r2.request.path = "/test"
        assert s._hash(r) == s._hash(r2)
        r2.request.path = "/test?param1=2"
        assert s._hash(r) == s._hash(r2)
        r2.request.path = "/test?param2=1"
        assert s._hash(r) == s._hash(r2)
        r2.request.path = "/test?param3=2"
        assert not s._hash(r) == s._hash(r2)


def thash(r, r2, setter):
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        s = serverplayback.ServerPlayback()
        tctx.configure(s, server_replay_ignore_payload_params=["param1", "param2"])

        setter(r, paramx="x", param1="1")

        setter(r2, paramx="x", param1="1")
        # same parameters
        assert s._hash(r) == s._hash(r2)
        # ignored parameters !=
        setter(r2, paramx="x", param1="2")
        assert s._hash(r) == s._hash(r2)
        # missing parameter
        setter(r2, paramx="x")
        assert s._hash(r) == s._hash(r2)
        # ignorable parameter added
        setter(r2, paramx="x", param1="2")
        assert s._hash(r) == s._hash(r2)
        # not ignorable parameter changed
        setter(r2, paramx="y", param1="1")
        assert not s._hash(r) == s._hash(r2)
        # not ignorable parameter missing
        setter(r2, param1="1")
        r2.request.content = b"param1=1"
        assert not s._hash(r) == s._hash(r2)


def test_ignore_payload_params():
    def urlencode_setter(r, **kwargs):
        r.request.content = urllib.parse.urlencode(kwargs).encode()

    r = tflow.tflow(resp=True)
    r.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
    r2 = tflow.tflow(resp=True)
    r2.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
    thash(r, r2, urlencode_setter)

    boundary = "somefancyboundary"

    def multipart_setter(r, **kwargs):
        b = f"--{boundary}\n"
        parts = []
        for k, v in kwargs.items():
            parts.append('Content-Disposition: form-data; name="%s"\n\n%s\n' % (k, v))
        c = b + b.join(parts) + b
        r.request.content = c.encode()
        r.request.headers["content-type"] = "multipart/form-data; boundary=" + boundary

    r = tflow.tflow(resp=True)
    r2 = tflow.tflow(resp=True)
    thash(r, r2, multipart_setter)


def test_runtime_modify_params():
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        r = tflow.tflow(resp=True)
        r.request.path = "/test?param1=1"
        r2 = tflow.tflow(resp=True)
        r2.request.path = "/test"

        s.load_flows([r])
        hash = next(iter(s.flowmap.keys()))

        tctx.configure(s, server_replay_ignore_params=["param1"])
        hash_mod = next(iter(s.flowmap.keys()))

        assert hash != hash_mod
        assert hash_mod == s._hash(r2)


def test_server_playback_full():
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        tctx.configure(
            s,
            server_replay_refresh=True,
        )

        f = tflow.tflow()
        f.response = mitmproxy.test.tutils.tresp(content=f.request.content)
        s.load_flows([f, f])

        tf = tflow.tflow()
        assert not tf.response
        s.request(tf)
        assert tf.response.data == f.response.data

        tf = tflow.tflow()
        tf.request.content = b"gibble"
        assert not tf.response
        s.request(tf)
        assert not tf.response


async def test_server_playback_kill():
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        tctx.configure(s, server_replay_refresh=True, server_replay_kill_extra=True)

        f = tflow.tflow()
        f.response = mitmproxy.test.tutils.tresp(content=f.request.content)
        s.load_flows([f])

        f = tflow.tflow()
        f.request.host = "nonexistent"
        await tctx.cycle(s, f)
        assert f.error


async def test_server_playback_kill_new_option():
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        tctx.configure(s, server_replay_refresh=True, server_replay_extra="kill")

        f = tflow.tflow()
        f.response = mitmproxy.test.tutils.tresp(content=f.request.content)
        s.load_flows([f])

        f = tflow.tflow()
        f.request.host = "nonexistent"
        await tctx.cycle(s, f)
        assert f.error


@pytest.mark.parametrize(
    "option,status",
    [
        ("204", 204),
        ("400", 400),
        ("404", 404),
        ("500", 500),
    ],
)
async def test_server_playback_404(option, status):
    s = serverplayback.ServerPlayback()
    with taddons.context(s) as tctx:
        tctx.configure(s, server_replay_refresh=True, server_replay_extra=option)

        f = tflow.tflow()
        f.response = mitmproxy.test.tutils.tresp(content=f.request.content)
        s.load_flows([f])

        f = tflow.tflow()
        f.request.host = "nonexistent"
        s.request(f)
        assert f.response.status_code == status


def test_server_playback_response_deleted():
    """
    The server playback addon holds references to flows that can be modified by the user in the meantime.
    One thing that can happen is that users remove the response object. This happens for example when doing a client
    replay at the same time.
    """
    sp = serverplayback.ServerPlayback()
    with taddons.context(sp) as tctx:
        tctx.configure(sp)
        f1 = tflow.tflow(resp=True)
        f2 = tflow.tflow(resp=True)

        assert not sp.flowmap

        sp.load_flows([f1, f2])
        assert sp.flowmap

        f1.response = f2.response = None
        assert not sp.next_flow(f1)
        assert not sp.flowmap


@pytest.fixture
def playback(monkeypatch):
    """ServerPlayback with in-memory options and no event loop or sockets."""
    sp = serverplayback.ServerPlayback()
    options = SimpleNamespace(
        server_replay_ignore_content=False,
        server_replay_ignore_payload_params=[],
        server_replay_ignore_host=False,
        server_replay_ignore_port=False,
        server_replay_ignore_params=[],
        server_replay_use_headers=[],
        server_replay_reuse=False,
        server_replay_nopop=False,
    )
    monkeypatch.setattr(ctx, "options", options, raising=False)
    monkeypatch.setattr(
        ctx,
        "master",
        SimpleNamespace(addons=SimpleNamespace(trigger=lambda hook: None)),
        raising=False,
    )
    return sp, options


def _replay_flow(path: str, body: bytes) -> http.HTTPFlow:
    f = tflow.tflow()
    f.request = http.Request.make("GET", "https://example.invalid" + path)
    f.response = http.Response.make(200, body)
    return f


def _selected(sp, path: str) -> bytes:
    selected = sp.next_flow(_replay_flow(path, b""))
    assert selected is not None
    return selected.response.content


def test_replay_path_params_distinguish_final_segment_values(playback):
    sp, _ = playback
    old = _replay_flow("/record;revision=old", b"old fixture")
    new = _replay_flow("/record;revision=new", b"new fixture")

    sp.load_flows([old, new])
    assert _selected(sp, "/record;revision=new") == b"new fixture"
    assert _selected(sp, "/record;revision=old") == b"old fixture"

    sp.load_flows([new, old])
    assert _selected(sp, "/record;revision=old") == b"old fixture"


def test_replay_path_params_present_absent_and_multiple(playback):
    sp, _ = playback
    sp.load_flows(
        [
            _replay_flow("/record;revision=new", b"with param"),
            _replay_flow("/record", b"without param"),
            _replay_flow("/record;a=1;b=2", b"a1b2"),
            _replay_flow("/record;a=1;b=3", b"a1b3"),
        ]
    )
    assert _selected(sp, "/record") == b"without param"
    assert _selected(sp, "/record;revision=new") == b"with param"
    assert _selected(sp, "/record;a=1;b=3") == b"a1b3"
    assert _selected(sp, "/record;a=1;b=2") == b"a1b2"


def test_replay_path_params_percent_encoded_semicolon(playback):
    sp, _ = playback
    sp.load_flows(
        [
            _replay_flow("/record%3Brevision=old", b"encoded old"),
            _replay_flow("/record%3Brevision=new", b"encoded new"),
            _replay_flow("/record;revision=old", b"literal old"),
        ]
    )
    assert _selected(sp, "/record%3Brevision=new") == b"encoded new"
    assert _selected(sp, "/record%3Brevision=old") == b"encoded old"
    assert _selected(sp, "/record;revision=old") == b"literal old"


def test_replay_path_params_survive_ignored_query(playback):
    sp, options = playback
    options.server_replay_ignore_params = ["token"]
    sp.load_flows(
        [
            _replay_flow("/record;revision=old?token=1", b"old fixture"),
            _replay_flow("/record;revision=new?token=2", b"new fixture"),
        ]
    )
    assert _selected(sp, "/record;revision=new?token=3") == b"new fixture"
    assert _selected(sp, "/record;revision=old?token=1") == b"old fixture"


def test_replay_path_params_query_only_ignore_matches_path(playback):
    sp, options = playback
    options.server_replay_ignore_params = ["token"]
    sp.load_flows([_replay_flow("/record;revision=new?token=abc", b"new fixture")])
    assert _selected(sp, "/record;revision=new?token=zzz") == b"new fixture"
    assert not sp.flowmap
    assert sp.next_flow(_replay_flow("/record;revision=new?token=zzz", b"")) is None


def test_replay_path_params_prior_segment_semicolon_unchanged(playback):
    sp, _ = playback
    sp.load_flows(
        [
            _replay_flow("/group;v=1/record", b"old fixture"),
            _replay_flow("/group;v=2/record", b"new fixture"),
        ]
    )
    assert _selected(sp, "/group;v=2/record") == b"new fixture"
    assert _selected(sp, "/group;v=1/record") == b"old fixture"


def test_replay_path_params_reuse_and_pop(playback):
    sp, options = playback
    sp.load_flows([_replay_flow("/record;revision=new", b"new fixture")])
    assert sp.next_flow(_replay_flow("/record;revision=old", b"")) is None
    assert _selected(sp, "/record;revision=new") == b"new fixture"
    assert not sp.flowmap

    options.server_replay_reuse = True
    sp.load_flows([_replay_flow("/record;revision=new", b"new fixture")])
    assert _selected(sp, "/record;revision=new") == b"new fixture"
    assert _selected(sp, "/record;revision=new") == b"new fixture"
    assert sp.count() == 1
