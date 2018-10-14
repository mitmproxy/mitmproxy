import binascii

import pytest

from unittest import mock
from mitmproxy import exceptions
from mitmproxy.addons import proxyauth
from mitmproxy.test import taddons
from mitmproxy.test import tflow


class TestMkauth:
    def test_mkauth_scheme(self):
        assert proxyauth.mkauth('username', 'password') == 'basic dXNlcm5hbWU6cGFzc3dvcmQ=\n'

    @pytest.mark.parametrize('scheme, expected', [
        ('', ' dXNlcm5hbWU6cGFzc3dvcmQ=\n'),
        ('basic', 'basic dXNlcm5hbWU6cGFzc3dvcmQ=\n'),
        ('foobar', 'foobar dXNlcm5hbWU6cGFzc3dvcmQ=\n'),
    ])
    def test_mkauth(self, scheme, expected):
        assert proxyauth.mkauth('username', 'password', scheme) == expected


class TestParseHttpBasicAuth:
    @pytest.mark.parametrize('input', [
        '',
        'foo bar',
        'basic abc',
        'basic ' + binascii.b2a_base64(b"foo").decode("ascii"),
    ])
    def test_parse_http_basic_auth_error(self, input):
        with pytest.raises(ValueError):
            proxyauth.parse_http_basic_auth(input)

    def test_parse_http_basic_auth(self):
        input = proxyauth.mkauth("test", "test")
        assert proxyauth.parse_http_basic_auth(input) == ("basic", "test", "test")


class TestProxyAuth:
    @pytest.mark.parametrize('mode, expected', [
        ('', False),
        ('foobar', False),
        ('regular', True),
        ('upstream:', True),
        ('upstream:foobar', True),
    ])
    def test_is_proxy_auth(self, mode, expected):
        up = proxyauth.ProxyAuth()
        with taddons.context(up, loadcore=False) as ctx:
            ctx.options.mode = mode
            assert up.is_proxy_auth() is expected

    @pytest.mark.parametrize('is_proxy_auth, expected', [
        (True, 'Proxy-Authorization'),
        (False, 'Authorization'),
    ])
    def test_which_auth_header(self, is_proxy_auth, expected):
        up = proxyauth.ProxyAuth()
        with mock.patch('mitmproxy.addons.proxyauth.ProxyAuth.is_proxy_auth', return_value=is_proxy_auth):
            assert up.which_auth_header() == expected

    @pytest.mark.parametrize('is_proxy_auth, expected_status_code, expected_header', [
        (True, 407, 'Proxy-Authenticate'),
        (False, 401, 'WWW-Authenticate'),
    ])
    def test_auth_required_response(self, is_proxy_auth, expected_status_code, expected_header):
        up = proxyauth.ProxyAuth()
        with mock.patch('mitmproxy.addons.proxyauth.ProxyAuth.is_proxy_auth', return_value=is_proxy_auth):
            resp = up.auth_required_response()
            assert resp.status_code == expected_status_code
            assert expected_header in resp.headers.keys()

    def test_check(self, tdata):
        up = proxyauth.ProxyAuth()
        with taddons.context(up) as ctx:
            ctx.configure(up, proxyauth="any", mode="regular")
            f = tflow.tflow()
            assert not up.check(f)
            f.request.headers["Proxy-Authorization"] = proxyauth.mkauth(
                "test", "test"
            )
            assert up.check(f)

            f.request.headers["Proxy-Authorization"] = "invalid"
            assert not up.check(f)

            f.request.headers["Proxy-Authorization"] = proxyauth.mkauth(
                "test", "test", scheme="unknown"
            )
            assert not up.check(f)

            ctx.configure(up, proxyauth="test:test")
            f.request.headers["Proxy-Authorization"] = proxyauth.mkauth(
                "test", "test"
            )
            assert up.check(f)
            ctx.configure(up, proxyauth="test:foo")
            assert not up.check(f)

            ctx.configure(
                up,
                proxyauth="@" + tdata.path(
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

            with mock.patch('ldap3.Server', return_value="ldap://fake_server:389 - cleartext"):
                with mock.patch('ldap3.Connection', search="test"):
                    with mock.patch('ldap3.Connection.search', return_value="test"):
                        ctx.configure(
                            up,
                            proxyauth="ldap:localhost:cn=default,dc=cdhdt,dc=com:password:ou=application,dc=cdhdt,dc=com"
                        )
                        f.request.headers["Proxy-Authorization"] = proxyauth.mkauth(
                            "test", "test"
                        )
                        assert up.check(f)
                        f.request.headers["Proxy-Authorization"] = proxyauth.mkauth(
                            "", ""
                        )
                        assert not up.check(f)

    def test_authenticate(self):
        up = proxyauth.ProxyAuth()
        with taddons.context(up, loadcore=False) as ctx:
            ctx.configure(up, proxyauth="any", mode="regular")

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
            ctx.configure(up, mode="reverse")
            assert not f.response
            up.authenticate(f)
            assert f.response.status_code == 401

            f = tflow.tflow()
            f.request.headers["Authorization"] = proxyauth.mkauth(
                "test", "test"
            )
            up.authenticate(f)
            assert not f.response
            assert not f.request.headers.get("Authorization")

    def test_configure(self, tdata):
        up = proxyauth.ProxyAuth()
        with taddons.context(up) as ctx:
            with pytest.raises(exceptions.OptionsError):
                ctx.configure(up, proxyauth="foo")

            ctx.configure(up, proxyauth="foo:bar")
            assert up.singleuser == ["foo", "bar"]

            ctx.configure(up, proxyauth=None)
            assert up.singleuser is None

            ctx.configure(up, proxyauth="any")
            assert up.nonanonymous
            ctx.configure(up, proxyauth=None)
            assert not up.nonanonymous

            with mock.patch('ldap3.Server', return_value="ldap://fake_server:389 - cleartext"):
                with mock.patch('ldap3.Connection', return_value="test"):
                    ctx.configure(up, proxyauth="ldap:localhost:cn=default,dc=cdhdt,dc=com:password:ou=application,dc=cdhdt,dc=com")
                    assert up.ldapserver
                    ctx.configure(up, proxyauth="ldaps:localhost:cn=default,dc=cdhdt,dc=com:password:ou=application,dc=cdhdt,dc=com")
                    assert up.ldapserver

            with pytest.raises(exceptions.OptionsError):
                ctx.configure(up, proxyauth="ldap:test:test:test")

            with pytest.raises(exceptions.OptionsError):
                ctx.configure(up, proxyauth="ldap:fake_serveruid=?dc=example,dc=com:person")

            with pytest.raises(exceptions.OptionsError):
                ctx.configure(up, proxyauth="ldapssssssss:fake_server:dn:password:tree")

            with pytest.raises(exceptions.OptionsError):
                ctx.configure(
                    up,
                    proxyauth= "@" + tdata.path("mitmproxy/net/data/server.crt")
                )
            with pytest.raises(exceptions.OptionsError):
                ctx.configure(up, proxyauth="@nonexistent")

            ctx.configure(
                up,
                proxyauth= "@" + tdata.path(
                    "mitmproxy/net/data/htpasswd"
                )
            )
            assert up.htpasswd
            assert up.htpasswd.check_password("test", "test")
            assert not up.htpasswd.check_password("test", "foo")
            ctx.configure(up, proxyauth=None)
            assert not up.htpasswd

            with pytest.raises(exceptions.OptionsError):
                ctx.configure(up, proxyauth="any", mode="transparent")
            with pytest.raises(exceptions.OptionsError):
                ctx.configure(up, proxyauth="any", mode="socks5")

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
            f.request.headers["Proxy-Authorization"] = proxyauth.mkauth(
                "test", "test"
            )
            up.http_connect(f)
            assert not f.response

            f2 = tflow.tflow(client_conn=f.client_conn)
            up.requestheaders(f2)
            assert not f2.response
            assert f2.metadata["proxyauth"] == ('test', 'test')
