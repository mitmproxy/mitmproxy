from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import io
from mitmproxy.addons import view, viewhttp2
from mitmproxy.tools.console import consoleaddons

import pytest

from mitmproxy.test import taddons
from mitmproxy.test import tflow


def tft(*, frame_type="HEADER", timestamp=0, flow=None):
    fl = tflow.thttp2flow(messages=True)
    if frame_type == "HEADER":
        f = fl.messages[0]
    elif frame_type == "PUSH_PROMISE":
        f = fl.messages[1]
    elif frame_type == "DATA":
        f = fl.messages[2]
    elif frame_type == "WINDOWS_UPDATE":
        f = fl.messages[3]
    elif frame_type == "SETTINGS":
        f = fl.messages[4]
    elif frame_type == "PING":
        f = fl.messages[5]
    elif frame_type == "PRIORITY":
        f = fl.messages[6]
    elif frame_type == "REST_STREAM":
        f = fl.messages[7]
    elif frame_type == "GOAWAY":
        f = fl.messages[8]

    if flow:
        f.flow = flow
        flow.messages.append(f)
    else:
        f.flow.messages = [f]
    f.timestamp = timestamp
    return f


def test_order_refresh():
    def save(*args, **kwargs):
        sargs.extend([args, kwargs])

    v = viewhttp2.ViewHttp2()
    sargs = []

    v.sig_view_refresh.connect(save)

    tf = tflow.thttp2flow().messages[0]
    with taddons.context() as tctx:
        tctx.configure(v, view_order_http2="time")
        v.add([tf])
        tf.timestamp = 10
        assert not sargs
        v.update([tf])
        assert sargs


def test_order_generators():
    v = viewhttp2.ViewHttp2()
    tf = tflow.thttp2flow().messages[0]

    rt = viewhttp2.OrderTimestamp(v)
    assert rt.generate(tf) == 945621202

    rft = viewhttp2.OrderFrameType(v)
    assert rft.generate(tf) == tf.frame_type

    rs = viewhttp2.OrderStreamID(v)
    assert rs.generate(tf) == tf.stream_id


def test_simple():
    v = viewhttp2.ViewHttp2()
    f = tft(timestamp=1)
    flow = f.flow

    assert v.store_count() == 0
    v.http2_frame(flow)
    assert list(v) == [f]
    assert v.get_by_id(f.id)
    assert not v.get_by_id("nonexistent")

    # These all just call update
    v.intercept(f)
    v.resume(f)
    assert list(v) == [f]

    v.http2_frame(f.flow)
    assert list(v) == [f]
    assert len(v._store) == 1
    assert v.store_count() == 1

    f2 = tft(timestamp=3, flow=flow)
    v.http2_frame(flow)
    assert list(v) == [f, f2]
    v.http2_frame(flow)
    assert list(v) == [f, f2]
    assert len(v._store) == 2

    assert v.inbounds(0)
    assert not v.inbounds(-1)
    assert not v.inbounds(100)

    f3 = tft(timestamp=4, flow=flow)
    v.http2_frame(flow)
    assert list(v) == [f, f2, f3]
    v.http2_frame(flow)
    assert list(v) == [f, f2, f3]
    assert len(v._store) == 3

    f.marked = not f.marked
    f2.marked = not f2.marked
    v.clear_not_marked()
    assert list(v) == [f, f2]
    assert len(v) == 2
    assert len(v._store) == 2

    v.clear()
    assert len(v) == 0
    assert len(v._store) == 0


def test_filter():
    v = viewhttp2.ViewHttp2()
    flow = tft(frame_type="HEADER").flow
    v.http2_frame(flow)
    v.http2_frame(tft(frame_type="DATA", flow=flow).flow)
    v.http2_frame(tft(frame_type="HEADER", flow=flow).flow)
    v.http2_frame(tft(frame_type="DATA", flow=flow).flow)
    assert(len(v)) == 4
    v.set_filter_cmd("~ft HEADER")
    assert [i.frame_type for i in v] == ["HEADER", "HEADER"]
    assert len(v._store) == 4
    v.set_filter(None)

    assert len(v) == 4
    v.toggle_marked()
    assert len(v) == 0
    v.toggle_marked()
    assert len(v) == 4

    with pytest.raises(exceptions.CommandError):
        v.set_filter_cmd("~notafilter regex")

    v[1].marked = True
    v.toggle_marked()
    assert len(v) == 1
    assert v[0].marked
    v.toggle_marked()
    assert len(v) == 4


def test_filtred_view():
    v = viewhttp2.ViewHttp2()
    v.add_filtred_view("~ft HEADER", "test_header")
    v.add_filtred_view("~ft PING", "test_ping")
    v.add_filtred_view("~ft WINDOWS_UPDATE", "test_windows_update")

    v.add([
        tft(frame_type="HEADER"),
        tft(frame_type="HEADER"),
        tft(frame_type="DATA"),
        tft(frame_type="PING"),
        tft(frame_type="GOAWAY"),
        tft(frame_type="HEADER"),
        tft(frame_type="PRIORITY")
    ])

    assert len(v.filtred_views["test_header"]) == 3
    assert v.filtred_views_focus["test_header"].item.frame_type == "HEADER"
    assert len(v.filtred_views["test_ping"]) == 1
    assert v.filtred_views_focus["test_ping"].item.frame_type == "PING"
    assert len(v.filtred_views["test_windows_update"]) == 0
    assert v.filtred_views_focus["test_windows_update"].item is None
    assert len(v) == 7

    v.clear()
    assert len(v.filtred_views["test_header"]) == 0
    assert len(v.filtred_views["test_ping"]) == 0
    assert len(v.filtred_views["test_windows_update"]) == 0

    with pytest.raises(exceptions.CommandError, match="Invalid interception filter:"):
        v.add_filtred_view("~noafilter", "test_bad")

    # Tests specific case for for focus
    assert v.inbounds(17, "test_header") is False
    assert v.inbounds(-5, "test_header") is False
    assert v.inbounds(4, "test_header") is False


def tdump(path, flows):
    with open(path, "wb") as f:
        w = io.FlowWriter(f)
        for i in flows:
            w.add(i)


@pytest.mark.asyncio
async def test_load(tmpdir):
    path = str(tmpdir.join("path"))
    v = viewhttp2.ViewHttp2()
    with taddons.context() as tctx:
        tctx.master.addons.add(v)
        tdump(
            path,
            [tflow.thttp2flow()]
        )
        v.load_file(path)
        assert len(v) == 9
        v.load_file(path)
        assert len(v) == 18
        try:
            v.load_file("nonexistent_file_path")
        except IOError:
            assert False
        with open(path, "wb") as f:
            f.write(b"invalidflows")
        v.load_file(path)
        assert await tctx.master.await_log("Invalid data format.")


def test_resolve():
    v = viewhttp2.ViewHttp2()
    with taddons.context() as tctx:
        flow = tft().flow
        assert tctx.command(v.resolve, "@all") == []
        assert tctx.command(v.resolve, "@focus") == []
        assert tctx.command(v.resolve, "@focus.http2") == []
        assert tctx.command(v.resolve, "@shown") == []
        assert tctx.command(v.resolve, "@shown.http2") == []
        assert tctx.command(v.resolve, "@hidden") == []
        assert tctx.command(v.resolve, "@hidden.http2") == []
        assert tctx.command(v.resolve, "@marked") == []
        assert tctx.command(v.resolve, "@unmarked") == []
        v.http2_frame(flow)
        assert len(tctx.command(v.resolve, "@focus")) == 1
        assert len(tctx.command(v.resolve, "@focus.http2")) == 1
        assert len(tctx.command(v.resolve, "@all")) == 1
        assert len(tctx.command(v.resolve, "@shown")) == 1
        assert len(tctx.command(v.resolve, "@shown.http2")) == 1
        assert len(tctx.command(v.resolve, "@unmarked")) == 1
        assert tctx.command(v.resolve, "@hidden") == []
        assert tctx.command(v.resolve, "@marked") == []
        v.http2_frame(tft(frame_type="DATA", flow=flow).flow)
        assert len(tctx.command(v.resolve, "@focus")) == 1
        assert len(tctx.command(v.resolve, "@focus.http2")) == 1
        assert len(tctx.command(v.resolve, "@shown")) == 2
        assert len(tctx.command(v.resolve, "@shown.http2")) == 2
        assert len(tctx.command(v.resolve, "@all")) == 2
        assert tctx.command(v.resolve, "@hidden") == []
        assert tctx.command(v.resolve, "@hidden.http2") == []
        assert tctx.command(v.resolve, "@marked") == []

        with pytest.raises(exceptions.CommandError, match="Invalid flow filter"):
            tctx.command(v.resolve, "~")

        # Resolve for filtred view
        v.add_filtred_view("~ft HEADER", "test_header")
        v.add_filtred_view("~ft DATA", "test_data")
        assert len(tctx.command(v.resolve, "@focus.http2.test_header")) == 1
        assert tctx.command(v.resolve, "@focus.http2.test_header")[0].frame_type == "HEADER"
        assert len(tctx.command(v.resolve, "@focus.http2.test_data")) == 1
        assert tctx.command(v.resolve, "@focus.http2.test_data")[0].frame_type == "DATA"
        assert len(tctx.command(v.resolve, "@shown.http2.test_header")) == 1
        assert tctx.command(v.resolve, "@shown.http2.test_header")[0].frame_type == "HEADER"
        assert len(tctx.command(v.resolve, "@shown.http2.test_data")) == 1
        assert tctx.command(v.resolve, "@shown.http2.test_data")[0].frame_type == "DATA"
        assert len(tctx.command(v.resolve, "@hidden.http2.test_header")) == 1
        assert tctx.command(v.resolve, "@hidden.http2.test_header")[0].frame_type == "DATA"
        assert len(tctx.command(v.resolve, "@hidden.http2.test_data")) == 1
        assert tctx.command(v.resolve, "@hidden.http2.test_data")[0].frame_type == "HEADER"


def test_movement():
    v = viewhttp2.ViewHttp2()
    v.add_filtred_view("~ft HEADER", "test_header")
    with taddons.context():
        v.go(0)
        v.f_go(0, "test_header")
        v.add([
            tft(),
            tft(),
            tft(),
            tft(),
            tft(),
        ])
        assert v.focus.index == 0
        assert v.filtred_views_focus["test_header"].index == 0
        v.go(-1)
        v.f_go(-1, "test_header")
        assert v.focus.index == 4
        assert v.filtred_views_focus["test_header"].index == 4
        v.go(0)
        v.f_go(0, "test_header")
        assert v.focus.index == 0
        assert v.filtred_views_focus["test_header"].index == 0
        v.go(1)
        v.f_go(1, "test_header")
        assert v.focus.index == 1
        assert v.filtred_views_focus["test_header"].index == 1
        v.go(999)
        v.f_go(999, "test_header")
        assert v.focus.index == 4
        assert v.filtred_views_focus["test_header"].index == 4
        v.go(-999)
        v.f_go(-999, "test_header")
        assert v.focus.index == 0
        assert v.filtred_views_focus["test_header"].index == 0

        v.focus_next()
        v.f_focus_next("test_header")
        assert v.focus.index == 1
        v.focus_prev()
        v.f_focus_prev("test_header")
        assert v.focus.index == 0


def test_duplicate():
    v = viewhttp2.ViewHttp2()
    with taddons.context():
        f = [
            tft(),
            tft()
        ]
        v.add(f)
        assert len(v) == 2
        v.duplicate(f)
        assert len(v) == 4
        assert v.focus.index == 2


def test_remove():
    v = viewhttp2.ViewHttp2()
    v.add_filtred_view("~ft HEADER", "test_header")
    with taddons.context():
        f = [tft(), tft(frame_type="DATA")]
        v.add(f)
        assert len(v) == 2
        assert len(v.filtred_views["test_header"]) == 1
        v.remove(f)
        assert len(v) == 0
        assert len(v.filtred_views["test_header"]) == 0


def test_order():
    v = viewhttp2.ViewHttp2()
    flow = tft(frame_type="HEADER", timestamp=1).flow
    v.http2_frame(flow)
    v.http2_frame(tft(frame_type="SETTINGS", timestamp=2, flow=flow).flow)
    v.http2_frame(tft(frame_type="DATA", timestamp=3, flow=flow).flow)
    v.http2_frame(tft(frame_type="HEADER", timestamp=4, flow=flow).flow)
    v.http2_frame(tft(frame_type="PUSH_PROMISE", timestamp=5, flow=flow).flow)
    v.http2_frame(tft(frame_type="DATA", timestamp=6, flow=flow).flow)
    v.http2_frame(tft(frame_type="PRIORITY", timestamp=7, flow=flow).flow)
    v.http2_frame(tft(frame_type="REST_STREAM", timestamp=8, flow=flow).flow)
    v.http2_frame(tft(frame_type="PING", timestamp=9, flow=flow).flow)
    v.http2_frame(tft(frame_type="GOAWAY", timestamp=10, flow=flow).flow)
    assert [i.timestamp for i in v] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    v.set_order("frame_type")
    assert v.get_order() == "frame_type"
    assert [i.frame_type for i in v] == ['DATA',
                                         'DATA',
                                         'GOAWAY',
                                         'HEADER',
                                         'HEADER',
                                         'PING',
                                         'PRIORITY',
                                         'PUSH_PROMISE',
                                         'RESET_STREAM',
                                         'SETTINGS']

    v.set_reversed(True)
    assert [i.frame_type for i in v] == ['SETTINGS',
                                         'RESET_STREAM',
                                         'PUSH_PROMISE',
                                         'PRIORITY',
                                         'PING',
                                         'HEADER',
                                         'HEADER',
                                         'GOAWAY',
                                         'DATA',
                                         'DATA']

    v.set_order("time")
    assert v.get_order() == "time"
    assert [i.timestamp for i in v] == [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

    v.set_reversed(False)
    assert [i.timestamp for i in v] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    with pytest.raises(exceptions.CommandError):
        v.set_order("not_an_order")


def test_reversed():
    v = viewhttp2.ViewHttp2()
    v.add_filtred_view("~ft DATA", "test_data")
    flow = tft(frame_type="HEADER", timestamp=1).flow
    v.http2_frame(flow)
    v.http2_frame(tft(frame_type="DATA", timestamp=2, flow=flow).flow)
    v.http2_frame(tft(frame_type="DATA", timestamp=3, flow=flow).flow)
    v.http2_frame(tft(frame_type="PING", timestamp=4, flow=flow).flow)
    v.set_reversed(True)

    assert v[0].timestamp == 4
    assert v[-1].timestamp == 1
    assert v[2].timestamp == 2
    with pytest.raises(IndexError):
        v[5]
    with pytest.raises(IndexError):
        v[-5]

    assert v._bisect(v[0]) == 1
    assert v._bisect(v[2]) == 3

    assert v._bisect(v[0], "test_data") == 1
    assert v._bisect(v[1], "test_data") == 1
    assert v._bisect(v[2], "test_data") == 2


def test_update():
    pass
    # TODO maybe ??


class Record:
    def __init__(self):
        self.calls = []

    def __bool__(self):
        return bool(self.calls)

    def __repr__(self):
        return repr(self.calls)

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def test_signals():
    v = viewhttp2.ViewHttp2()
    rec_add = Record()
    rec_update = Record()
    rec_remove = Record()
    rec_refresh = Record()

    def clearrec():
        rec_add.calls = []
        rec_update.calls = []
        rec_remove.calls = []
        rec_refresh.calls = []

    v.sig_view_add.connect(rec_add)
    v.sig_view_update.connect(rec_update)
    v.sig_view_remove.connect(rec_remove)
    v.sig_view_refresh.connect(rec_refresh)

    assert not any([rec_add, rec_update, rec_remove, rec_refresh])

    # Simple add
    v.add([tft(frame_type="HEADER")])
    assert rec_add
    assert not any([rec_update, rec_remove, rec_refresh])

    # Filter change triggers refresh
    clearrec()
    v.set_filter(flowfilter.parse("~ft DATA"))
    assert rec_refresh
    assert not any([rec_update, rec_add, rec_remove])

    v.set_filter(flowfilter.parse("~ft HEADER"))

    # An update that results in a flow being added to the view
    clearrec()
    v[0].frame_type = "DATA"
    v.update([v[0]])
    assert rec_remove
    assert not any([rec_update, rec_refresh, rec_add])

    # An update that does not affect the view just sends update
    v.set_filter(flowfilter.parse("~ft DATA"))
    clearrec()
    v.update([v[0]])
    assert rec_update
    assert not any([rec_remove, rec_refresh, rec_add])

    # An update for a flow in state but not view does not do anything
    f = v[0]
    v.set_filter(flowfilter.parse("~ft PING"))
    assert not len(v)
    clearrec()
    v.update([f])
    assert not any([rec_add, rec_update, rec_remove, rec_refresh])


def test_focus_follow():
    v = viewhttp2.ViewHttp2()
    v.add_filtred_view("~ft HEADER", "test_header")
    with taddons.context(v) as tctx:
        console_addon = consoleaddons.ConsoleAddon(tctx.master)
        tctx.configure(console_addon)
        tctx.configure(v, console_focus_follow=True, view_filter_http2="~ft HEADER")

        v.add([tft(timestamp=5)])
        assert v.focus.index == 0
        assert v.filtred_views_focus["test_header"].index == 0

        v.add([tft(timestamp=4)])
        assert v.focus.index == 0
        assert v.filtred_views_focus["test_header"].index == 0
        assert v.focus.item.timestamp == 4
        assert v.filtred_views_focus["test_header"].item.timestamp == 4

        v.add([tft(timestamp=7)])
        assert v.focus.index == 2
        assert v.filtred_views_focus["test_header"].index == 2
        assert v.focus.item.timestamp == 7
        assert v.filtred_views_focus["test_header"].item.timestamp == 7

        mod = tft(frame_type="DATA", timestamp=6)
        v.add([mod])
        assert v.focus.index == 2
        assert v.filtred_views_focus["test_header"].index == 2
        assert v.focus.item.timestamp == 7
        assert v.filtred_views_focus["test_header"].item.timestamp == 7

        mod.frame_type = "HEADER"
        v.update([mod])
        assert v.focus.index == 2
        assert v.filtred_views_focus["test_header"].index == 2
        assert v.focus.item.timestamp == 6
        assert v.filtred_views_focus["test_header"].item.timestamp == 6


def test_focus():
    # Special case - initialising with a view that already contains data
    v = viewhttp2.ViewHttp2()
    v.add([tft()])
    f = view.Focus(v)
    assert f.index is 0
    assert f.item is v[0]

    # Start empty
    v = viewhttp2.ViewHttp2()
    v.add_filtred_view("~ft DATA", "test_data")
    f = view.Focus(v)
    assert f.index is None
    assert f.item is None

    v.add([tft(timestamp=1)])
    assert f.index == 0
    assert f.item is v[0]

    # Try to set to something not in view
    with pytest.raises(ValueError):
        f.__setattr__("item", tft())
    with pytest.raises(ValueError):
        f.__setattr__("index", 99)

    v.add([tft(timestamp=0)])
    assert f.index == 1
    assert f.item is v[1]

    v.add([tft(timestamp=2)])
    assert f.index == 1
    assert f.item is v[1]

    f.index = 0
    assert f.index == 0
    f.index = 1

    v.remove([v[1]])
    assert f.index == 1
    assert f.item is v[1]

    v.remove([v[1]])
    assert f.index == 0
    assert f.item is v[0]

    v.remove([v[0]])
    assert f.index is None
    assert f.item is None

    flow = tft(frame_type="HEADER", timestamp=0).flow
    v.add([
        flow.messages[0],
        tft(frame_type="DATA", timestamp=1),
        tft(frame_type="PING", timestamp=2),
        tft(frame_type="GOAWAY", timestamp=3),
    ])

    f.item = v[2]
    assert f.item.frame_type == "PING"

    filt = flowfilter.parse("~ft PING")
    v.set_filter(filt)
    assert f.index == 0

    filt = flowfilter.parse("~ft oink")
    v.set_filter(filt)
    assert f.index is None

    f2 = v.filtred_views_focus["test_data"]
    v.set_filter(None)

    assert f2.index == 0
    assert v.focus is not None

    v.set_filter(flowfilter.parse("~ft oink"), "test_data")
    assert f2.index is None


def test_settings():
    v = viewhttp2.ViewHttp2()
    f = tft()

    with pytest.raises(KeyError):
        v.settings[f]
    v.add([f])
    v.settings[f]["foo"] = "bar"
    assert v.settings[f]["foo"] == "bar"
    assert len(list(v.settings)) == 1
    v.remove([f])
    with pytest.raises(KeyError):
        v.settings[f]
    assert not v.settings.keys()

    v.add([f])
    v.settings[f]["foo"] = "bar"
    assert v.settings.keys()
    v.clear()
    assert not v.settings.keys()


def test_properties():
    v = viewhttp2.ViewHttp2()
    v.add_filtred_view("~ft HEADER", "test_header")
    v.add_filtred_view("~ft DATA", "test_data")
    f = tft()
    v.http2_frame(f.flow)
    assert v.get_length() == 1
    assert len(v.filtred_views["test_header"]) == 1
    assert len(v.filtred_views["test_data"]) == 0
    assert not v.get_marked()
    v.toggle_marked()
    assert v.get_length() == 0
    assert len(v.filtred_views["test_header"]) == 0
    assert len(v.filtred_views["test_data"]) == 0
    assert v.get_marked()


def test_configure():
    v = viewhttp2.ViewHttp2()
    with taddons.context(v) as tctx:
        tctx.configure(v, view_filter_http2="~q")
        with pytest.raises(Exception, match="Invalid interception filter"):
            tctx.configure(v, view_filter_http2="~~")

        tctx.configure(v, view_order_http2="frame_type")
        with pytest.raises(Exception, match="Unknown flow order"):
            tctx.configure(v, view_order_http2="no")

        tctx.configure(v, view_order_reversed=True)

        tctx.configure(v, console_focus_follow=True)
        assert v.focus_follow
