from mitmproxy.addons import view
from mitmproxy import flowfilter

from .. import tutils


def test_simple():
    v = view.View()
    f = tutils.tflow()
    f.request.timestamp_start = 1
    v.request(f)
    assert list(v) == [f]
    v.request(f)
    assert list(v) == [f]
    assert len(v._store) == 1

    f2 = tutils.tflow()
    f2.request.timestamp_start = 3
    v.request(f2)
    assert list(v) == [f, f2]
    v.request(f2)
    assert list(v) == [f, f2]
    assert len(v._store) == 2

    f3 = tutils.tflow()
    f3.request.timestamp_start = 2
    v.request(f3)
    assert list(v) == [f, f3, f2]
    v.request(f3)
    assert list(v) == [f, f3, f2]
    assert len(v._store) == 3


def tft(*, method="get", start=0):
    f = tutils.tflow()
    f.request.method = method
    f.request.timestamp_start = start
    return f


def test_filter():
    v = view.View()
    f = flowfilter.parse("~m get")
    v.request(tft(method="get"))
    v.request(tft(method="put"))
    v.request(tft(method="get"))
    v.request(tft(method="put"))
    assert(len(v)) == 4
    v.set_filter(f)
    assert [i.request.method for i in v] == ["GET", "GET"]
    assert len(v._store) == 4
    v.set_filter(None)


def test_order():
    v = view.View()
    v.request(tft(method="get", start=1))
    v.request(tft(method="put", start=2))
    v.request(tft(method="get", start=3))
    v.request(tft(method="put", start=4))
    assert [i.request.timestamp_start for i in v] == [1, 2, 3, 4]

    v.set_order(view.key_request_method)
    assert [i.request.method for i in v] == ["GET", "GET", "PUT", "PUT"]
    v.order_reverse = True
    assert [i.request.method for i in v] == ["PUT", "PUT", "GET", "GET"]

    v.set_order(view.key_request_start)
    assert [i.request.timestamp_start for i in v] == [4, 3, 2, 1]

    v.order_reverse = False
    assert [i.request.timestamp_start for i in v] == [1, 2, 3, 4]


def test_update():
    v = view.View()
    flt = flowfilter.parse("~m get")
    v.set_filter(flt)

    f = tft(method="get")
    v.request(f)
    assert f in v

    f.request.method = "put"
    v.update(f)
    assert f not in v

    f.request.method = "get"
    v.update(f)
    assert f in v

    v.update(f)
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

    v.sig_add.connect(rec_add)
    v.sig_update.connect(rec_update)
    v.sig_remove.connect(rec_remove)
    v.sig_refresh.connect(rec_refresh)

    assert not any([rec_add, rec_update, rec_remove, rec_refresh])

    # Simple add
    v.add(tft())
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
    v.update(v[0])
    assert rec_remove
    assert not any([rec_update, rec_refresh, rec_add])

    # An update that does not affect the view just sends update
    v.set_filter(flowfilter.parse("~m put"))
    clearrec()
    v.update(v[0])
    assert rec_update
    assert not any([rec_remove, rec_refresh, rec_add])

    # An update for a flow in state but not view does not do anything
    f = v[0]
    v.set_filter(flowfilter.parse("~m get"))
    assert not len(v)
    clearrec()
    v.update(f)
    assert not any([rec_add, rec_update, rec_remove, rec_refresh])
