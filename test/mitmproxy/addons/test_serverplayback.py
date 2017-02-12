import os
import urllib

from mitmproxy.test import tutils
from mitmproxy.test import tflow
from mitmproxy.test import taddons

import mitmproxy.test.tutils
from mitmproxy.addons import serverplayback
from mitmproxy import options
from mitmproxy import exceptions
from mitmproxy import io


def tdump(path, flows):
    w = io.FlowWriter(open(path, "wb"))
    for i in flows:
        w.add(i)


def test_config():
    s = serverplayback.ServerPlayback()
    with tutils.tmpdir() as p:
        with taddons.context() as tctx:
            fpath = os.path.join(p, "flows")
            tdump(fpath, [tflow.tflow(resp=True)])
            tctx.configure(s, server_replay=[fpath])
            tutils.raises(
                exceptions.OptionsError,
                tctx.configure,
                s,
                server_replay=[p]
            )


def test_tick():
    s = serverplayback.ServerPlayback()
    with taddons.context() as tctx:
        s.stop = True
        s.final_flow = tflow.tflow()
        s.final_flow.live = False
        s.tick()
        assert tctx.master.should_exit.is_set()


def test_server_playback():
    sp = serverplayback.ServerPlayback()
    sp.configure(options.Options(), [])
    f = tflow.tflow(resp=True)

    assert not sp.flowmap

    sp.load([f])
    assert sp.flowmap
    assert sp.next_flow(f)
    assert not sp.flowmap

    sp.load([f])
    assert sp.flowmap
    sp.clear()
    assert not sp.flowmap


def test_ignore_host():
    sp = serverplayback.ServerPlayback()
    sp.configure(options.Options(server_replay_ignore_host=True), [])

    r = tflow.tflow(resp=True)
    r2 = tflow.tflow(resp=True)

    r.request.host = "address"
    r2.request.host = "address"
    assert sp._hash(r) == sp._hash(r2)
    r2.request.host = "wrong_address"
    assert sp._hash(r) == sp._hash(r2)


def test_ignore_content():
    s = serverplayback.ServerPlayback()
    s.configure(options.Options(server_replay_ignore_content=False), [])

    r = tflow.tflow(resp=True)
    r2 = tflow.tflow(resp=True)

    r.request.content = b"foo"
    r2.request.content = b"foo"
    assert s._hash(r) == s._hash(r2)
    r2.request.content = b"bar"
    assert not s._hash(r) == s._hash(r2)

    s.configure(options.Options(server_replay_ignore_content=True), [])
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
    s.configure(
        options.Options(
            server_replay_ignore_content=True,
            server_replay_ignore_payload_params=[
                "param1", "param2"
            ]
        ),
        []
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
    with taddons.context() as tctx:
        tctx.configure(
            s,
            server_replay_ignore_content=False,
            server_replay_ignore_payload_params=[
                "param1", "param2"
            ]
        )

        r = tflow.tflow(resp=True)
        r.request.headers["Content-Type"] = "application/json"
        r.request.content = b'{"param1":"1"}'
        r2 = tflow.tflow(resp=True)
        r2.request.headers["Content-Type"] = "application/json"
        r2.request.content = b'{"param1":"1"}'
        # same content
        assert s._hash(r) == s._hash(r2)
        # distint content (note only x-www-form-urlencoded payload is analysed)
        r2.request.content = b'{"param1":"2"}'
        assert not s._hash(r) == s._hash(r2)


def test_hash():
    s = serverplayback.ServerPlayback()
    s.configure(options.Options(), [])

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
    s.configure(options.Options(server_replay_use_headers=["foo"]), [])

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
    s.configure(options.Options(), [])

    r = tflow.tflow(resp=True)
    r.request.headers["key"] = "one"

    r2 = tflow.tflow(resp=True)
    r2.request.headers["key"] = "two"

    s.load([r, r2])

    assert s.count() == 2

    n = s.next_flow(r)
    assert n.request.headers["key"] == "one"
    assert s.count() == 1

    n = s.next_flow(r)
    assert n.request.headers["key"] == "two"
    assert not s.flowmap
    assert s.count() == 0

    assert not s.next_flow(r)


def test_load_with_server_replay_nopop():
    s = serverplayback.ServerPlayback()
    s.configure(options.Options(server_replay_nopop=True), [])

    r = tflow.tflow(resp=True)
    r.request.headers["key"] = "one"

    r2 = tflow.tflow(resp=True)
    r2.request.headers["key"] = "two"

    s.load([r, r2])

    assert s.count() == 2
    s.next_flow(r)
    assert s.count() == 2


def test_ignore_params():
    s = serverplayback.ServerPlayback()
    s.configure(
        options.Options(
            server_replay_ignore_params=["param1", "param2"]
        ),
        []
    )

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
    s.configure(
        options.Options(
            server_replay_ignore_payload_params=["param1", "param2"]
        ),
        []
    )

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

    boundary = 'somefancyboundary'

    def multipart_setter(r, **kwargs):
        b = "--{0}\n".format(boundary)
        parts = []
        for k, v in kwargs.items():
            parts.append(
                "Content-Disposition: form-data; name=\"%s\"\n\n"
                "%s\n" % (k, v)
            )
        c = b + b.join(parts) + b
        r.request.content = c.encode()
        r.request.headers["content-type"] = 'multipart/form-data; boundary=' +\
            boundary

    r = tflow.tflow(resp=True)
    r2 = tflow.tflow(resp=True)
    thash(r, r2, multipart_setter)


def test_server_playback_full():
    s = serverplayback.ServerPlayback()
    with taddons.context() as tctx:
        tctx.configure(
            s,
            refresh_server_playback = True,
            keepserving=False
        )

        f = tflow.tflow()
        f.response = mitmproxy.test.tutils.tresp(content=f.request.content)
        s.load([f, f])

        tf = tflow.tflow()
        assert not tf.response
        s.request(tf)
        assert tf.response == f.response

        tf = tflow.tflow()
        tf.request.content = b"gibble"
        assert not tf.response
        s.request(tf)
        assert not tf.response

        assert not s.stop
        s.tick()
        assert not s.stop

        tf = tflow.tflow()
        s.request(tflow.tflow())
        assert s.stop


def test_server_playback_kill():
    s = serverplayback.ServerPlayback()
    with taddons.context() as tctx:
        tctx.configure(
            s,
            refresh_server_playback = True,
            replay_kill_extra=True
        )

        f = tflow.tflow()
        f.response = mitmproxy.test.tutils.tresp(content=f.request.content)
        s.load([f])

        f = tflow.tflow()
        f.request.host = "nonexistent"
        tctx.cycle(s, f)
        assert f.reply.value == exceptions.Kill
