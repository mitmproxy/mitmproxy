import binascii

from mitmproxy import exceptions
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.addons import proxyauth


def test_parse_http_basic_auth():
    assert proxyauth.parse_http_basic_auth(
        proxyauth.mkauth("test", "test")
    ) == ("basic", "test", "test")
    assert not proxyauth.parse_http_basic_auth("")
    assert not proxyauth.parse_http_basic_auth("foo bar")
    v = "basic " + binascii.b2a_base64(b"foo").decode("ascii")
    assert not proxyauth.parse_http_basic_auth(v)


def test_configure():
    up = proxyauth.ProxyAuth()
    with taddons.context() as ctx:
        tutils.raises(
            exceptions.OptionsError,
            ctx.configure, up, auth_singleuser="foo"
        )

        ctx.configure(up, auth_singleuser="foo:bar")
        assert up.singleuser == ["foo", "bar"]

        ctx.configure(up, auth_singleuser=None)
        assert up.singleuser is None

        ctx.configure(up, auth_nonanonymous=True)
        assert up.nonanonymous
        ctx.configure(up, auth_nonanonymous=False)
        assert not up.nonanonymous

        tutils.raises(
            exceptions.OptionsError,
            ctx.configure,
            up,
            auth_htpasswd = tutils.test_data.path(
                "mitmproxy/net/data/server.crt"
            )
        )
        tutils.raises(
            exceptions.OptionsError,
            ctx.configure,
            up,
            auth_htpasswd = "nonexistent"
        )

        ctx.configure(
            up,
            auth_htpasswd = tutils.test_data.path(
                "mitmproxy/net/data/htpasswd"
            )
        )
        assert up.htpasswd
        assert up.htpasswd.check_password("test", "test")
        assert not up.htpasswd.check_password("test", "foo")
        ctx.configure(up, auth_htpasswd = None)
        assert not up.htpasswd

        tutils.raises(
            exceptions.OptionsError,
            ctx.configure,
            up,
            auth_nonanonymous = True,
            mode = "transparent"
        )
        tutils.raises(
            exceptions.OptionsError,
            ctx.configure,
            up,
            auth_nonanonymous = True,
            mode = "socks5"
        )


def test_check():
    up = proxyauth.ProxyAuth()
    with taddons.context() as ctx:
        ctx.configure(up, auth_nonanonymous=True)
        f = tflow.tflow()
        assert not up.check(f)
        f.request.headers["Proxy-Authorization"] = proxyauth.mkauth(
            "test", "test"
        )
        assert up.check(f)

        f.request.headers["Proxy-Authorization"] = "invalid"
        assert not up.check(f)

        f.request.headers["Proxy-Authorization"] = proxyauth.mkauth(
            "test", "test", scheme = "unknown"
        )
        assert not up.check(f)

        ctx.configure(up, auth_nonanonymous=False, auth_singleuser="test:test")
        f.request.headers["Proxy-Authorization"] = proxyauth.mkauth(
            "test", "test"
        )
        assert up.check(f)
        ctx.configure(up, auth_nonanonymous=False, auth_singleuser="test:foo")
        assert not up.check(f)

        ctx.configure(
            up,
            auth_singleuser = None,
            auth_htpasswd = tutils.test_data.path(
                "mitmproxy/net/data/htpasswd"
            )
        )
        f.request.headers["Proxy-Authorization"] = proxyauth.mkauth(
            "test", "test"
        )
        assert up.check(f)
        f.request.headers["Proxy-Authorization"] = proxyauth.mkauth(
            "test", "foo"
        )
        assert not up.check(f)


def test_authenticate():
    up = proxyauth.ProxyAuth()
    with taddons.context() as ctx:
        ctx.configure(up, auth_nonanonymous=True)

        f = tflow.tflow()
        assert not f.response
        up.authenticate(f)
        assert f.response.status_code == 407

        f = tflow.tflow()
        f.request.headers["Proxy-Authorization"] = proxyauth.mkauth(
            "test", "test"
        )
        up.authenticate(f)
        assert not f.response
        assert not f.request.headers.get("Proxy-Authorization")

        f = tflow.tflow()
        f.mode = "transparent"
        assert not f.response
        up.authenticate(f)
        assert f.response.status_code == 401

        f = tflow.tflow()
        f.mode = "transparent"
        f.request.headers["Authorization"] = proxyauth.mkauth(
            "test", "test"
        )
        up.authenticate(f)
        assert not f.response
        assert not f.request.headers.get("Authorization")


def test_handlers():
    up = proxyauth.ProxyAuth()
    with taddons.context() as ctx:
        ctx.configure(up, auth_nonanonymous=True)

        f = tflow.tflow()
        assert not f.response
        up.requestheaders(f)
        assert f.response.status_code == 407

        f = tflow.tflow()
        f.request.method = "CONNECT"
        assert not f.response
        up.http_connect(f)
        assert f.response.status_code == 407
