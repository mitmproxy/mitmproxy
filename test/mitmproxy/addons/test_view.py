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
