from .. import tutils, mastertest

import netlib.tutils
from mitmproxy.builtins import serverplayback
from mitmproxy import options
from mitmproxy import exceptions
from mitmproxy import flow


class TestServerPlayback:
    def test_server_playback(self):
        sp = serverplayback.ServerPlayback()
        sp.configure(options.Options(), [])
        f = tutils.tflow(resp=True)

        assert not sp.flowmap

        sp.load([f])
        assert sp.flowmap
        assert sp.next_flow(f)
        assert not sp.flowmap

    def test_ignore_host(self):
        sp = serverplayback.ServerPlayback()
        sp.configure(options.Options(server_replay_ignore_host=True), [])

        r = tutils.tflow(resp=True)
        r2 = tutils.tflow(resp=True)

        r.request.host = "address"
        r2.request.host = "address"
        assert sp._hash(r) == sp._hash(r2)
        r2.request.host = "wrong_address"
        assert sp._hash(r) == sp._hash(r2)

    def test_ignore_content(self):
        s = serverplayback.ServerPlayback()
        s.configure(options.Options(server_replay_ignore_content=False), [])

        r = tutils.tflow(resp=True)
        r2 = tutils.tflow(resp=True)

        r.request.content = b"foo"
        r2.request.content = b"foo"
        assert s._hash(r) == s._hash(r2)
        r2.request.content = b"bar"
        assert not s._hash(r) == s._hash(r2)

        s.configure(options.Options(server_replay_ignore_content=True), [])
        r = tutils.tflow(resp=True)
        r2 = tutils.tflow(resp=True)
        r.request.content = b"foo"
        r2.request.content = b"foo"
        assert s._hash(r) == s._hash(r2)
        r2.request.content = b"bar"
        assert s._hash(r) == s._hash(r2)
        r2.request.content = b""
        assert s._hash(r) == s._hash(r2)
        r2.request.content = None
        assert s._hash(r) == s._hash(r2)

    def test_ignore_content_wins_over_params(self):
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

        r = tutils.tflow(resp=True)
        r.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        r.request.content = b"paramx=y"

        r2 = tutils.tflow(resp=True)
        r2.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        r2.request.content = b"paramx=x"

        # same parameters
        assert s._hash(r) == s._hash(r2)

    def test_ignore_payload_params_other_content_type(self):
        s = serverplayback.ServerPlayback()
        s.configure(
            options.Options(
                server_replay_ignore_content=False,
                server_replay_ignore_payload_params=[
                    "param1", "param2"
                ]
            ),
            []

        )
        r = tutils.tflow(resp=True)
        r.request.headers["Content-Type"] = "application/json"
        r.request.content = b'{"param1":"1"}'
        r2 = tutils.tflow(resp=True)
        r2.request.headers["Content-Type"] = "application/json"
        r2.request.content = b'{"param1":"1"}'
        # same content
        assert s._hash(r) == s._hash(r2)
        # distint content (note only x-www-form-urlencoded payload is analysed)
        r2.request.content = b'{"param1":"2"}'
        assert not s._hash(r) == s._hash(r2)

    def test_hash(self):
        s = serverplayback.ServerPlayback()
        s.configure(options.Options(), [])

        r = tutils.tflow()
        r2 = tutils.tflow()

        assert s._hash(r)
        assert s._hash(r) == s._hash(r2)
        r.request.headers["foo"] = "bar"
        assert s._hash(r) == s._hash(r2)
        r.request.path = "voing"
        assert s._hash(r) != s._hash(r2)

        r.request.path = "path?blank_value"
        r2.request.path = "path?"
        assert s._hash(r) != s._hash(r2)

    def test_headers(self):
        s = serverplayback.ServerPlayback()
        s.configure(options.Options(server_replay_use_headers=["foo"]), [])

        r = tutils.tflow(resp=True)
        r.request.headers["foo"] = "bar"
        r2 = tutils.tflow(resp=True)
        assert not s._hash(r) == s._hash(r2)
        r2.request.headers["foo"] = "bar"
        assert s._hash(r) == s._hash(r2)
        r2.request.headers["oink"] = "bar"
        assert s._hash(r) == s._hash(r2)

        r = tutils.tflow(resp=True)
        r2 = tutils.tflow(resp=True)
        assert s._hash(r) == s._hash(r2)

    def test_load(self):
        s = serverplayback.ServerPlayback()
        s.configure(options.Options(), [])

        r = tutils.tflow(resp=True)
        r.request.headers["key"] = "one"

        r2 = tutils.tflow(resp=True)
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

    def test_load_with_server_replay_nopop(self):
        s = serverplayback.ServerPlayback()
        s.configure(options.Options(server_replay_nopop=True), [])

        r = tutils.tflow(resp=True)
        r.request.headers["key"] = "one"

        r2 = tutils.tflow(resp=True)
        r2.request.headers["key"] = "two"

        s.load([r, r2])

        assert s.count() == 2
        s.next_flow(r)
        assert s.count() == 2

    def test_ignore_params(self):
        s = serverplayback.ServerPlayback()
        s.configure(
            options.Options(
                server_replay_ignore_params=["param1", "param2"]
            ),
            []
        )

        r = tutils.tflow(resp=True)
        r.request.path = "/test?param1=1"
        r2 = tutils.tflow(resp=True)
        r2.request.path = "/test"
        assert s._hash(r) == s._hash(r2)
        r2.request.path = "/test?param1=2"
        assert s._hash(r) == s._hash(r2)
        r2.request.path = "/test?param2=1"
        assert s._hash(r) == s._hash(r2)
        r2.request.path = "/test?param3=2"
        assert not s._hash(r) == s._hash(r2)

    def test_ignore_payload_params(self):
        s = serverplayback.ServerPlayback()
        s.configure(
            options.Options(
                server_replay_ignore_payload_params=["param1", "param2"]
            ),
            []
        )

        r = tutils.tflow(resp=True)
        r.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        r.request.content = b"paramx=x&param1=1"
        r2 = tutils.tflow(resp=True)
        r2.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        r2.request.content = b"paramx=x&param1=1"
        # same parameters
        assert s._hash(r) == s._hash(r2)
        # ignored parameters !=
        r2.request.content = b"paramx=x&param1=2"
        assert s._hash(r) == s._hash(r2)
        # missing parameter
        r2.request.content = b"paramx=x"
        assert s._hash(r) == s._hash(r2)
        # ignorable parameter added
        r2.request.content = b"paramx=x&param1=2"
        assert s._hash(r) == s._hash(r2)
        # not ignorable parameter changed
        r2.request.content = b"paramx=y&param1=1"
        assert not s._hash(r) == s._hash(r2)
        # not ignorable parameter missing
        r2.request.content = b"param1=1"
        assert not s._hash(r) == s._hash(r2)

    def test_server_playback_full(self):
        state = flow.State()
        s = serverplayback.ServerPlayback()
        o = options.Options(refresh_server_playback = True, keepserving=False)
        m = mastertest.RecordingMaster(o, None, state)
        m.addons.add(o, s)

        f = tutils.tflow()
        f.response = netlib.tutils.tresp(content=f.request.content)
        s.load([f, f])

        tf = tutils.tflow()
        assert not tf.response
        m.request(tf)
        assert tf.response == f.response

        tf = tutils.tflow()
        tf.request.content = b"gibble"
        assert not tf.response
        m.request(tf)
        assert not tf.response

        assert not s.stop
        s.tick()
        assert not s.stop

        tf = tutils.tflow()
        m.request(tutils.tflow())
        assert s.stop

    def test_server_playback_kill(self):
        state = flow.State()
        s = serverplayback.ServerPlayback()
        o = options.Options(refresh_server_playback = True, replay_kill_extra=True)
        m = mastertest.RecordingMaster(o, None, state)
        m.addons.add(o, s)

        f = tutils.tflow()
        f.response = netlib.tutils.tresp(content=f.request.content)
        s.load([f])

        f = tutils.tflow()
        f.request.host = "nonexistent"
        m.request(f)
        assert f.reply.value == exceptions.Kill
