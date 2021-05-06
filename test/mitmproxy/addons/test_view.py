import pytest

from mitmproxy.test import tflow

from mitmproxy.addons import view
from mitmproxy import flowfilter
from mitmproxy import exceptions
from mitmproxy import io
from mitmproxy.test import taddons
from mitmproxy.tools.console import consoleaddons
from mitmproxy.tools.console.common import render_marker, SYMBOL_MARK


def tft(*, method="get", start=0):
    f = tflow.tflow()
    f.request.method = method
    f.request.timestamp_start = start
    return f


def test_order_refresh():
    v = view.View()
    sargs = []

    def save(*args, **kwargs):
        sargs.extend([args, kwargs])

    v.sig_view_refresh.connect(save)

    tf = tflow.tflow(resp=True)
    with taddons.context() as tctx:
        tctx.configure(v, view_order="time")
        v.add([tf])
        tf.request.timestamp_start = 10
        assert not sargs
        v.update([tf])
        assert sargs


def test_order_generators_http():
    v = view.View()
    tf = tflow.tflow(resp=True)

    rs = view.OrderRequestStart(v)
    assert rs.generate(tf) == 946681200

    rm = view.OrderRequestMethod(v)
    assert rm.generate(tf) == tf.request.method

    ru = view.OrderRequestURL(v)
    assert ru.generate(tf) == tf.request.url

    sz = view.OrderKeySize(v)
    assert sz.generate(tf) == len(tf.request.raw_content) + len(tf.response.raw_content)


def test_order_generators_tcp():
    v = view.View()
    tf = tflow.ttcpflow()

    rs = view.OrderRequestStart(v)
    assert rs.generate(tf) == 946681200

    rm = view.OrderRequestMethod(v)
    assert rm.generate(tf) == "TCP"

    ru = view.OrderRequestURL(v)
    assert ru.generate(tf) == "address:22"

    sz = view.OrderKeySize(v)
    assert sz.generate(tf) == sum(len(m.content) for m in tf.messages)


def test_simple():
    v = view.View()
    f = tft(start=1)
    assert v.store_count() == 0
    v.request(f)
    assert list(v) == [f]
    assert v.get_by_id(f.id)
    assert not v.get_by_id("nonexistent")

    # These all just call update
    v.error(f)
    v.response(f)
    v.intercept(f)
    v.resume(f)
    v.kill(f)
    assert list(v) == [f]

    v.request(f)
    assert list(v) == [f]
    assert len(v._store) == 1
    assert v.store_count() == 1

    f2 = tft(start=3)
    v.request(f2)
    assert list(v) == [f, f2]
    v.request(f2)
    assert list(v) == [f, f2]
    assert len(v._store) == 2

    assert v.inbounds(0)
    assert not v.inbounds(-1)
    assert not v.inbounds(100)

    f3 = tft(start=2)
    v.request(f3)
    assert list(v) == [f, f3, f2]
    v.request(f3)
    assert list(v) == [f, f3, f2]
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


def test_simple_tcp():
    v = view.View()
    f = tflow.ttcpflow()
    assert v.store_count() == 0
    v.tcp_start(f)
    assert list(v) == [f]

    # These all just call update
    v.tcp_start(f)
    v.tcp_message(f)
    v.tcp_error(f)
    v.tcp_end(f)
    assert list(v) == [f]


def test_filter():
    v = view.View()
    v.request(tft(method="get"))
    v.request(tft(method="put"))
    v.request(tft(method="get"))
    v.request(tft(method="put"))
    assert(len(v)) == 4
    v.set_filter_cmd("~m get")
    assert [i.request.method for i in v] == ["GET", "GET"]
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


def tdump(path, flows):
    with open(path, "wb") as f:
        w = io.FlowWriter(f)
        for i in flows:
            w.add(i)


def test_create():
    v = view.View()
    with taddons.context():
        v.create("get", "http://foo.com")
        assert len(v) == 1
        assert v[0].request.url == "http://foo.com/"
        v.create("get", "http://foo.com")
        assert len(v) == 2
        with pytest.raises(exceptions.CommandError, match="Invalid URL"):
            v.create("get", "http://foo.com\\")
        with pytest.raises(exceptions.CommandError, match="Invalid URL"):
            v.create("get", "http://")


def test_orders():
    v = view.View()
    with taddons.context(v):
        assert v.order_options()


@pytest.mark.asyncio
async def test_load(tmpdir):
    path = str(tmpdir.join("path"))
    v = view.View()
    with taddons.context() as tctx:
        tctx.master.addons.add(v)
        tdump(
            path,
            [
                tflow.tflow(resp=True),
                tflow.tflow(resp=True)
            ]
        )
        v.load_file(path)
        assert len(v) == 2
        v.load_file(path)
        assert len(v) == 4
        try:
            v.load_file("nonexistent_file_path")
        except OSError:
            assert False
        with open(path, "wb") as f:
            f.write(b"invalidflows")
        v.load_file(path)
        await tctx.master.await_log("Invalid data format.")


def test_resolve():
    v = view.View()
    with taddons.context() as tctx:
        assert tctx.command(v.resolve, "@all") == []
        assert tctx.command(v.resolve, "@focus") == []
        assert tctx.command(v.resolve, "@shown") == []
        assert tctx.command(v.resolve, "@hidden") == []
        assert tctx.command(v.resolve, "@marked") == []
        assert tctx.command(v.resolve, "@unmarked") == []
        assert tctx.command(v.resolve, "~m get") == []
        v.request(tft(method="get"))
        assert len(tctx.command(v.resolve, "~m get")) == 1
        assert len(tctx.command(v.resolve, "@focus")) == 1
        assert len(tctx.command(v.resolve, "@all")) == 1
        assert len(tctx.command(v.resolve, "@shown")) == 1
        assert len(tctx.command(v.resolve, "@unmarked")) == 1
        assert tctx.command(v.resolve, "@hidden") == []
        assert tctx.command(v.resolve, "@marked") == []
        v.request(tft(method="put"))
        assert len(tctx.command(v.resolve, "@focus")) == 1
        assert len(tctx.command(v.resolve, "@shown")) == 2
        assert len(tctx.command(v.resolve, "@all")) == 2
        assert tctx.command(v.resolve, "@hidden") == []
        assert tctx.command(v.resolve, "@marked") == []

        v.request(tft(method="get"))
        v.request(tft(method="put"))

        f = flowfilter.parse("~m get")
        v.set_filter(f)
        v[0].marked = True

        def m(l):
            return [i.request.method for i in l]

        assert m(tctx.command(v.resolve, "~m get")) == ["GET", "GET"]
        assert m(tctx.command(v.resolve, "~m put")) == ["PUT", "PUT"]
        assert m(tctx.command(v.resolve, "@shown")) == ["GET", "GET"]
        assert m(tctx.command(v.resolve, "@hidden")) == ["PUT", "PUT"]
        assert m(tctx.command(v.resolve, "@marked")) == ["GET"]
        assert m(tctx.command(v.resolve, "@unmarked")) == ["PUT", "GET", "PUT"]
        assert m(tctx.command(v.resolve, "@all")) == ["GET", "PUT", "GET", "PUT"]

        with pytest.raises(exceptions.CommandError, match="Invalid flow filter"):
            tctx.command(v.resolve, "~")


def test_movement():
    v = view.View()
    with taddons.context():
        v.go(0)
        v.add([
            tflow.tflow(),
            tflow.tflow(),
            tflow.tflow(),
            tflow.tflow(),
            tflow.tflow(),
        ])
        assert v.focus.index == 0
        v.go(-1)
        assert v.focus.index == 4
        v.go(0)
        assert v.focus.index == 0
        v.go(1)
        assert v.focus.index == 1
        v.go(999)
        assert v.focus.index == 4
        v.go(-999)
        assert v.focus.index == 0

        v.focus_next()
        assert v.focus.index == 1
        v.focus_prev()
        assert v.focus.index == 0


def test_duplicate():
    v = view.View()
    with taddons.context():
        f = [
            tflow.tflow(),
            tflow.tflow(),
        ]
        v.add(f)
        assert len(v) == 2
        v.duplicate(f)
        assert len(v) == 4
        assert v.focus.index == 2


def test_remove():
    v = view.View()
    with taddons.context():
        f = [tflow.tflow(), tflow.tflow()]
        v.add(f)
        assert len(v) == 2
        v.remove(f)
        assert len(v) == 0


def test_setgetval():
    v = view.View()
    with taddons.context():
        f = tflow.tflow()
        v.add([f])
        v.setvalue([f], "key", "value")
        assert v.getvalue(f, "key", "default") == "value"
        assert v.getvalue(f, "unknow", "default") == "default"

        v.setvalue_toggle([f], "key")
        assert v.getvalue(f, "key", "default") == "true"
        v.setvalue_toggle([f], "key")
        assert v.getvalue(f, "key", "default") == "false"


def test_order():
    v = view.View()
    v.request(tft(method="get", start=1))
    v.request(tft(method="put", start=2))
    v.request(tft(method="get", start=3))
    v.request(tft(method="put", start=4))
    assert [i.request.timestamp_start for i in v] == [1, 2, 3, 4]

    v.set_order("method")
    assert v.get_order() == "method"
    assert [i.request.method for i in v] == ["GET", "GET", "PUT", "PUT"]
    v.set_reversed(True)
    assert [i.request.method for i in v] == ["PUT", "PUT", "GET", "GET"]

    v.set_order("time")
    assert v.get_order() == "time"
    assert [i.request.timestamp_start for i in v] == [4, 3, 2, 1]

    v.set_reversed(False)
    assert [i.request.timestamp_start for i in v] == [1, 2, 3, 4]
    with pytest.raises(exceptions.CommandError):
        v.set_order("not_an_order")


def test_reversed():
    v = view.View()
    v.request(tft(start=1))
    v.request(tft(start=2))
    v.request(tft(start=3))
    v.set_reversed(True)

    assert v[0].request.timestamp_start == 3
    assert v[-1].request.timestamp_start == 1
    assert v[2].request.timestamp_start == 1
    with pytest.raises(IndexError):
        v[5]
    with pytest.raises(IndexError):
        v[-5]

    assert v._bisect(v[0]) == 1
    assert v._bisect(v[2]) == 3


def test_update():
    v = view.View()
    flt = flowfilter.parse("~m get")
    v.set_filter(flt)

    f = tft(method="get")
    v.request(f)
    assert f in v

    f.request.method = "put"
    v.update([f])
    assert f not in v

    f.request.method = "get"
    v.update([f])
    assert f in v

    v.update([f])
    assert f in v


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
    v = view.View()
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
    v.add([tft()])
    assert rec_add
    assert not any([rec_update, rec_remove, rec_refresh])

    # Filter change triggers refresh
    clearrec()
    v.set_filter(flowfilter.parse("~m put"))
    assert rec_refresh
    assert not any([rec_update, rec_add, rec_remove])

    v.set_filter(flowfilter.parse("~m get"))

    # An update that results in a flow being added to the view
    clearrec()
    v[0].request.method = "PUT"
    v.update([v[0]])
    assert rec_remove
    assert not any([rec_update, rec_refresh, rec_add])

    # An update that does not affect the view just sends update
    v.set_filter(flowfilter.parse("~m put"))
    clearrec()
    v.update([v[0]])
    assert rec_update
    assert not any([rec_remove, rec_refresh, rec_add])

    # An update for a flow in state but not view does not do anything
    f = v[0]
    v.set_filter(flowfilter.parse("~m get"))
    assert not len(v)
    clearrec()
    v.update([f])
    assert not any([rec_add, rec_update, rec_remove, rec_refresh])


def test_focus_follow():
    v = view.View()
    with taddons.context(v) as tctx:
        console_addon = consoleaddons.ConsoleAddon(tctx.master)
        tctx.configure(console_addon)
        tctx.configure(v, console_focus_follow=True, view_filter="~m get")

        v.add([tft(start=5)])
        assert v.focus.index == 0

        v.add([tft(start=4)])
        assert v.focus.index == 0
        assert v.focus.flow.request.timestamp_start == 4

        v.add([tft(start=7)])
        assert v.focus.index == 2
        assert v.focus.flow.request.timestamp_start == 7

        mod = tft(method="put", start=6)
        v.add([mod])
        assert v.focus.index == 2
        assert v.focus.flow.request.timestamp_start == 7

        mod.request.method = "GET"
        v.update([mod])
        assert v.focus.index == 2
        assert v.focus.flow.request.timestamp_start == 6


def test_focus():
    # Special case - initialising with a view that already contains data
    v = view.View()
    v.add([tft()])
    f = view.Focus(v)
    assert f.index == 0
    assert f.flow is v[0]

    # Start empty
    v = view.View()
    f = view.Focus(v)
    assert f.index is None
    assert f.flow is None

    v.add([tft(start=1)])
    assert f.index == 0
    assert f.flow is v[0]

    # Try to set to something not in view
    with pytest.raises(ValueError):
        f.__setattr__("flow", tft())
    with pytest.raises(ValueError):
        f.__setattr__("index", 99)

    v.add([tft(start=0)])
    assert f.index == 1
    assert f.flow is v[1]

    v.add([tft(start=2)])
    assert f.index == 1
    assert f.flow is v[1]

    f.index = 0
    assert f.index == 0
    f.index = 1

    v.remove([v[1]])
    v[1].intercept()
    assert f.index == 1
    assert f.flow is v[1]

    v.remove([v[1]])
    assert f.index == 0
    assert f.flow is v[0]

    v.remove([v[0]])
    assert f.index is None
    assert f.flow is None

    v.add([
        tft(method="get", start=0),
        tft(method="get", start=1),
        tft(method="put", start=2),
        tft(method="get", start=3),
    ])

    f.flow = v[2]
    assert f.flow.request.method == "PUT"

    filt = flowfilter.parse("~m get")
    v.set_filter(filt)
    assert f.index == 2

    filt = flowfilter.parse("~m oink")
    v.set_filter(filt)
    assert f.index is None


def test_settings():
    v = view.View()
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
    v = view.View()
    f = tft()
    v.request(f)
    assert v.get_length() == 1
    assert not v.get_marked()
    v.toggle_marked()
    assert v.get_length() == 0
    assert v.get_marked()


def test_configure():
    v = view.View()
    with taddons.context(v) as tctx:
        tctx.configure(v, view_filter="~q")
        with pytest.raises(Exception, match="Invalid interception filter"):
            tctx.configure(v, view_filter="~~")

        tctx.configure(v, view_order="method")
        with pytest.raises(Exception, match="Unknown flow order"):
            tctx.configure(v, view_order="no")

        tctx.configure(v, view_order_reversed=True)

        tctx.configure(v, console_focus_follow=True)
        assert v.focus_follow


@pytest.mark.parametrize("marker, expected", [
    [":default:", SYMBOL_MARK],
    ["X", "X"],
    [":grapes:", "\N{grapes}"],
    [":not valid:", SYMBOL_MARK], [":weird", SYMBOL_MARK]
])
def test_marker(marker, expected):
    assert render_marker(marker) == expected