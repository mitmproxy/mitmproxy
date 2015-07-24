import binascii

from netlib import odict, http
from netlib.http import authentication
from .. import tutils


def test_parse_http_basic_auth():
    vals = ("basic", "foo", "bar")
    assert http.authentication.parse_http_basic_auth(
        http.authentication.assemble_http_basic_auth(*vals)
    ) == vals
    assert not http.authentication.parse_http_basic_auth("")
    assert not http.authentication.parse_http_basic_auth("foo bar")
    v = "basic " + binascii.b2a_base64("foo")
    assert not http.authentication.parse_http_basic_auth(v)


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
        h = odict.ODictCaseless()
        assert ba.auth_challenge_headers()
        assert not ba.authenticate(h)

    def test_authenticate_clean(self):
        ba = authentication.BasicProxyAuth(authentication.PassManNonAnon(), "test")

        hdrs = odict.ODictCaseless()
        vals = ("basic", "foo", "bar")
        hdrs[ba.AUTH_HEADER] = [authentication.assemble_http_basic_auth(*vals)]
        assert ba.authenticate(hdrs)

        ba.clean(hdrs)
        assert not ba.AUTH_HEADER in hdrs

        hdrs[ba.AUTH_HEADER] = [""]
        assert not ba.authenticate(hdrs)

        hdrs[ba.AUTH_HEADER] = ["foo"]
        assert not ba.authenticate(hdrs)

        vals = ("foo", "foo", "bar")
        hdrs[ba.AUTH_HEADER] = [authentication.assemble_http_basic_auth(*vals)]
        assert not ba.authenticate(hdrs)

        ba = authentication.BasicProxyAuth(authentication.PassMan(), "test")
        vals = ("basic", "foo", "bar")
        hdrs[ba.AUTH_HEADER] = [authentication.assemble_http_basic_auth(*vals)]
        assert not ba.authenticate(hdrs)


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
