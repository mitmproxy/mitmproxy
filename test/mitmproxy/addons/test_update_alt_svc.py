from mitmproxy import http
from mitmproxy.addons import update_alt_svc
from mitmproxy.proxy.mode_specs import ProxyMode
from mitmproxy.test import taddons
from mitmproxy.test import tflow


def test_simple():
    header = 'h3="example.com:443"; ma=3600, h2=":443"; ma=3600'
    modified = update_alt_svc.update_alt_svc_header(header, 1234)
    assert modified == 'h3=":1234"; ma=3600, h2=":1234"; ma=3600'


def test_updates_alt_svc_header():
    upd = update_alt_svc.UpdateAltSvc()
    with taddons.context(upd) as ctx:
        headers = http.Headers(
            host="example.com",
            content_type="application/xml",
            alt_svc='h3="example.com:443"; ma=3600, h2=":443"; ma=3600',
        )
        resp = tflow.tresp(headers=headers)
        f = tflow.tflow(resp=resp)
        f.client_conn.sockname = ("", 1234)

        upd.responseheaders(f)
        assert (
            f.response.headers["alt-svc"]
            == 'h3="example.com:443"; ma=3600, h2=":443"; ma=3600'
        )

        ctx.options.keep_alt_svc_header = True
        f.client_conn.proxy_mode = ProxyMode.parse("reverse:https://example.com")
        upd.responseheaders(f)
        assert (
            f.response.headers["alt-svc"]
            == 'h3="example.com:443"; ma=3600, h2=":443"; ma=3600'
        )

        ctx.options.keep_alt_svc_header = False
        upd.responseheaders(f)
        assert (
            f.response.headers["alt-svc"] == 'h3=":1234"; ma=3600, h2=":1234"; ma=3600'
        )
