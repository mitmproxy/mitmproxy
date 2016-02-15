import binascii

from netlib import tutils
from netlib.http import authentication, Headers


def test_parse_http_basic_auth():
    vals = ("basic", "foo", "bar")
    assert authentication.parse_http_basic_auth(
        authentication.assemble_http_basic_auth(*vals)
    ) == vals
    assert not authentication.parse_http_basic_auth("")
    assert not authentication.parse_http_basic_auth("foo bar")
    v = "basic " + binascii.b2a_base64(b"foo").decode("ascii")
    assert not authentication.parse_http_basic_auth(v)


class TestPassManNonAnon:

    def test_simple(self):
        p = authentication.PassManNonAnon()
        assert not p.test("", "")
        assert p.test("user", "")


class TestPassManHtpasswd:

    def test_file_errors(self):
        tutils.raises(
            "malformed htpasswd file",
            authentication.PassManHtpasswd,
            tutils.test_data.path("data/server.crt"))

    def test_simple(self):
        pm = authentication.PassManHtpasswd(tutils.test_data.path("data/htpasswd"))

        vals = ("basic", "test", "test")
        authentication.assemble_http_basic_auth(*vals)
        assert pm.test("test", "test")
        assert not pm.test("test", "foo")
        assert not pm.test("foo", "test")
        assert not pm.test("test", "")
        assert not pm.test("", "")


class TestPassManSingleUser:

    def test_simple(self):
        pm = authentication.PassManSingleUser("test", "test")
        assert pm.test("test", "test")
        assert not pm.test("test", "foo")
        assert not pm.test("foo", "test")


class TestNullProxyAuth:

    def test_simple(self):
        na = authentication.NullProxyAuth(authentication.PassManNonAnon())
        assert not na.auth_challenge_headers()
        assert na.authenticate("foo")
        na.clean({})


class TestBasicProxyAuth:

    def test_simple(self):
        ba = authentication.BasicProxyAuth(authentication.PassManNonAnon(), "test")
        headers = Headers()
        assert ba.auth_challenge_headers()
        assert not ba.authenticate(headers)

    def test_authenticate_clean(self):
        ba = authentication.BasicProxyAuth(authentication.PassManNonAnon(), "test")

        headers = Headers()
        vals = ("basic", "foo", "bar")
        headers[ba.AUTH_HEADER] = authentication.assemble_http_basic_auth(*vals)
        assert ba.authenticate(headers)

        ba.clean(headers)
        assert not ba.AUTH_HEADER in headers

        headers[ba.AUTH_HEADER] = ""
        assert not ba.authenticate(headers)

        headers[ba.AUTH_HEADER] = "foo"
        assert not ba.authenticate(headers)

        vals = ("foo", "foo", "bar")
        headers[ba.AUTH_HEADER] = authentication.assemble_http_basic_auth(*vals)
        assert not ba.authenticate(headers)

        ba = authentication.BasicProxyAuth(authentication.PassMan(), "test")
        vals = ("basic", "foo", "bar")
        headers[ba.AUTH_HEADER] = authentication.assemble_http_basic_auth(*vals)
        assert not ba.authenticate(headers)


class Bunch:
    pass


class TestAuthAction:

    def test_nonanonymous(self):
        m = Bunch()
        aa = authentication.NonanonymousAuthAction(None, "authenticator")
        aa(None, m, None, None)
        assert m.authenticator

    def test_singleuser(self):
        m = Bunch()
        aa = authentication.SingleuserAuthAction(None, "authenticator")
        aa(None, m, "foo:bar", None)
        assert m.authenticator
        tutils.raises("invalid", aa, None, m, "foo", None)

    def test_httppasswd(self):
        m = Bunch()
        aa = authentication.HtpasswdAuthAction(None, "authenticator")
        aa(None, m, tutils.test_data.path("data/htpasswd"), None)
        assert m.authenticator
