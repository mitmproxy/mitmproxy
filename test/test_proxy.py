from libmproxy import proxy
import tutils


def test_proxy_error():
    p = proxy.ProxyError(111, "msg")
    assert str(p)


def test_app_registry():
    ar = proxy.AppRegistry()
    ar.add("foo", "domain", 80)

    r = tutils.treq()
    r.host = "domain"
    r.port = 80
    assert ar.get(r)

    r.port = 81
    assert not ar.get(r)


    r = tutils.treq()
    r.host = "domain2"
    r.port = 80
    assert not ar.get(r)
    r.headers["host"] = ["domain"]
    assert ar.get(r)
