import binascii
from unittest import mock

import ldap3
import pytest

from mitmproxy import exceptions
from mitmproxy.addons import proxyauth
from mitmproxy.proxy.layers import modes
from mitmproxy.test import taddons
from mitmproxy.test import tflow


class TestMkauth:
    def test_mkauth_scheme(self):
        assert (
            proxyauth.mkauth("username", "password")
            == "basic dXNlcm5hbWU6cGFzc3dvcmQ=\n"
        )

    @pytest.mark.parametrize(
        "scheme, expected",
        [
            ("", " dXNlcm5hbWU6cGFzc3dvcmQ=\n"),
            ("basic", "basic dXNlcm5hbWU6cGFzc3dvcmQ=\n"),
            ("foobar", "foobar dXNlcm5hbWU6cGFzc3dvcmQ=\n"),
        ],
    )
    def test_mkauth(self, scheme, expected):
        assert proxyauth.mkauth("username", "password", scheme) == expected


class TestParseHttpBasicAuth:
    @pytest.mark.parametrize(
        "input",
        [
            "",
            "foo bar",
            "basic abc",
            "basic " + binascii.b2a_base64(b"foo").decode("ascii"),
        ],
    )
    def test_parse_http_basic_auth_error(self, input):
        with pytest.raises(ValueError):
            proxyauth.parse_http_basic_auth(input)

    def test_parse_http_basic_auth(self):
        input = proxyauth.mkauth("test", "test")
        assert proxyauth.parse_http_basic_auth(input) == ("basic", "test", "test")


class TestProxyAuth:
    @pytest.mark.parametrize(
        "mode, expected",
        [
            ("", False),
            ("foobar", False),
            ("regular", True),
            ("upstream:", True),
            ("upstream:foobar", True),
        ],
    )
    def test_is_http_proxy(self, mode, expected):
        up = proxyauth.ProxyAuth()
        with taddons.context(up, loadcore=False) as ctx:
            ctx.options.mode = mode
            assert up.is_http_proxy is expected

    @pytest.mark.parametrize(
        "is_http_proxy, expected",
        [
            (True, "Proxy-Authorization"),
            (False, "Authorization"),
        ],
    )
    def test_which_auth_header(self, is_http_proxy, expected):
        up = proxyauth.ProxyAuth()
        with mock.patch(
            "mitmproxy.addons.proxyauth.ProxyAuth.is_http_proxy", new=is_http_proxy
        ):
            assert up.http_auth_header == expected

    @pytest.mark.parametrize(
        "is_http_proxy, expected_status_code, expected_header",
        [
            (True, 407, "Proxy-Authenticate"),
            (False, 401, "WWW-Authenticate"),
        ],
    )
    def test_auth_required_response(
        self, is_http_proxy, expected_status_code, expected_header
    ):
        up = proxyauth.ProxyAuth()
        with mock.patch(
            "mitmproxy.addons.proxyauth.ProxyAuth.is_http_proxy", new=is_http_proxy
        ):
            resp = up.make_auth_required_response()
            assert resp.status_code == expected_status_code
            assert expected_header in resp.headers.keys()

    def test_socks5(self):
        pa = proxyauth.ProxyAuth()
        with taddons.context(pa, loadcore=False) as ctx:
            ctx.configure(pa, proxyauth="foo:bar", mode="regular")
            data = modes.Socks5AuthData(tflow.tclient_conn(), "foo", "baz")
            pa.socks5_auth(data)
            assert not data.valid
            data.password = "bar"
            pa.socks5_auth(data)
            assert data.valid

    def test_authenticate(self):
        up = proxyauth.ProxyAuth()
        with taddons.context(up, loadcore=False) as ctx:
            ctx.configure(up, proxyauth="any", mode="regular")

            f = tflow.tflow()
            assert not f.response
            up.authenticate_http(f)
            assert f.response.status_code == 407

            f = tflow.tflow()
            f.request.headers["Proxy-Authorization"] = proxyauth.mkauth("test", "test")
            up.authenticate_http(f)
            assert not f.response
            assert not f.request.headers.get("Proxy-Authorization")

            f = tflow.tflow()
            ctx.configure(up, mode="reverse")
            assert not f.response
            up.authenticate_http(f)
            assert f.response.status_code == 401

            f = tflow.tflow()
            f.request.headers["Authorization"] = proxyauth.mkauth("test", "test")
            up.authenticate_http(f)
            assert not f.response
            assert not f.request.headers.get("Authorization")

    def test_configure(self, monkeypatch, tdata):
        monkeypatch.setattr(ldap3, "Server", mock.MagicMock())
        monkeypatch.setattr(ldap3, "Connection", mock.MagicMock())

        pa = proxyauth.ProxyAuth()
        with taddons.context(pa) as ctx:
            with pytest.raises(
                exceptions.OptionsError, match="Invalid proxyauth specification"
            ):
                ctx.configure(pa, proxyauth="foo")

            ctx.configure(pa, proxyauth="foo:bar")
            assert isinstance(pa.validator, proxyauth.SingleUser)
            assert pa.validator("foo", "bar")
            assert not pa.validator("foo", "baz")

            with pytest.raises(
                exceptions.OptionsError, match="Invalid single-user auth specification."
            ):
                ctx.configure(pa, proxyauth="foo:bar:baz")

            ctx.configure(pa, proxyauth="any")
            assert isinstance(pa.validator, proxyauth.AcceptAll)
            assert pa.validator("foo", "bar")

            ctx.configure(pa, proxyauth=None)
            assert pa.validator is None

            ctx.configure(
                pa,
                proxyauth="ldap:localhost:cn=default,dc=cdhdt,dc=com:password:ou=application,dc=cdhdt,dc=com",
            )
            assert isinstance(pa.validator, proxyauth.Ldap)

            ctx.configure(
                pa,
                proxyauth="ldap:localhost:1234:cn=default,dc=cdhdt,dc=com:password:ou=application,dc=cdhdt,dc=com",
            )
            assert isinstance(pa.validator, proxyauth.Ldap)

            with pytest.raises(
                exceptions.OptionsError, match="Invalid LDAP specification"
            ):
                ctx.configure(pa, proxyauth="ldap:test:test:test")

            with pytest.raises(
                exceptions.OptionsError, match="Invalid LDAP specification"
            ):
                ctx.configure(
                    pa, proxyauth="ldap:fake_serveruid=?dc=example,dc=com:person"
                )

            with pytest.raises(
                exceptions.OptionsError, match="Invalid LDAP specification"
            ):
                ctx.configure(pa, proxyauth="ldapssssssss:fake_server:dn:password:tree")

            with pytest.raises(
                exceptions.OptionsError, match="Could not open htpasswd file"
            ):
                ctx.configure(
                    pa, proxyauth="@" + tdata.path("mitmproxy/net/data/server.crt")
                )
            with pytest.raises(
                exceptions.OptionsError, match="Could not open htpasswd file"
            ):
                ctx.configure(pa, proxyauth="@nonexistent")

            ctx.configure(pa, proxyauth="@" + tdata.path("mitmproxy/net/data/htpasswd"))
            assert isinstance(pa.validator, proxyauth.Htpasswd)
            assert pa.validator("test", "test")
            assert not pa.validator("test", "foo")

            with pytest.raises(
                exceptions.OptionsError,
                match="Proxy Authentication not supported in transparent mode.",
            ):
                ctx.configure(pa, proxyauth="any", mode="transparent")

    def test_handlers(self):
        up = proxyauth.ProxyAuth()
        with taddons.context(up) as ctx:
            ctx.configure(up, proxyauth="any", mode="regular")

            f = tflow.tflow()
            assert not f.response
            up.requestheaders(f)
            assert f.response.status_code == 407

            f = tflow.tflow()
            f.request.method = "CONNECT"
            assert not f.response
            up.http_connect(f)
            assert f.response.status_code == 407

            f = tflow.tflow()
            f.request.method = "CONNECT"
            f.request.headers["Proxy-Authorization"] = proxyauth.mkauth("test", "test")
            up.http_connect(f)
            assert not f.response

            f2 = tflow.tflow(client_conn=f.client_conn)
            up.requestheaders(f2)
            assert not f2.response
            assert f2.metadata["proxyauth"] == ("test", "test")


@pytest.mark.parametrize(
    "spec",
    [
        "ldaps:localhost:cn=default,dc=cdhdt,dc=com:password:ou=application,dc=cdhdt,dc=com",
        "ldap:localhost:1234:cn=default,dc=cdhdt,dc=com:password:ou=application,dc=cdhdt,dc=com",
    ],
)
def test_ldap(monkeypatch, spec):
    monkeypatch.setattr(ldap3, "Server", mock.MagicMock())
    monkeypatch.setattr(ldap3, "Connection", mock.MagicMock())

    validator = proxyauth.Ldap(spec)
    assert not validator("", "")
    assert validator("foo", "bar")
    validator.conn.response = False
    assert not validator("foo", "bar")
