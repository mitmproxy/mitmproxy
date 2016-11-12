import binascii

from mitmproxy import exceptions
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.addons import proxyauth


def test_parse_http_basic_auth():
    vals = ("basic", "foo", "bar")
    assert proxyauth.parse_http_basic_auth(
        proxyauth.assemble_http_basic_auth(*vals)
    ) == vals
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
