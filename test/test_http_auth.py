import binascii, cStringIO
from netlib import odict, http_auth, http
import mock
import tutils

class TestPassManNonAnon:
    def test_simple(self):
        p = http_auth.PassManNonAnon()
        assert not p.test("", "")
        assert p.test("user", "")


class TestPassManHtpasswd:
    def test_file_errors(self):
        s = cStringIO.StringIO("foo")
        tutils.raises("invalid htpasswd", http_auth.PassManHtpasswd, s)
        s = cStringIO.StringIO("foo:bar$foo")
        tutils.raises("invalid htpasswd", http_auth.PassManHtpasswd, s)

    def test_simple(self):
        f = open(tutils.test_data.path("data/htpasswd"),"rb")
        pm = http_auth.PassManHtpasswd(f)

        vals = ("basic", "test", "test")
        p = http.assemble_http_basic_auth(*vals)
        assert pm.test("test", "test")
        assert not pm.test("test", "foo")
        assert not pm.test("foo", "test")
        assert not pm.test("test", "")
        assert not pm.test("", "")


class TestPassManSingleUser:
    def test_simple(self):
        pm = http_auth.PassManSingleUser("test", "test")
        assert pm.test("test", "test")
        assert not pm.test("test", "foo")
        assert not pm.test("foo", "test")


class TestNullProxyAuth:
    def test_simple(self):
        na = http_auth.NullProxyAuth(http_auth.PassManNonAnon())
        assert not na.auth_challenge_headers()
        assert na.authenticate("foo")
        na.clean({})


class TestBasicProxyAuth:
    def test_simple(self):
        ba = http_auth.BasicProxyAuth(http_auth.PassManNonAnon(), "test")
        h = odict.ODictCaseless()
        assert ba.auth_challenge_headers()
        assert not ba.authenticate(h)

    def test_authenticate_clean(self):
        ba = http_auth.BasicProxyAuth(http_auth.PassManNonAnon(), "test")

        hdrs = odict.ODictCaseless()
        vals = ("basic", "foo", "bar")
        hdrs[ba.AUTH_HEADER] = [http.assemble_http_basic_auth(*vals)]
        assert ba.authenticate(hdrs)

        ba.clean(hdrs)
        assert not ba.AUTH_HEADER in hdrs


        hdrs[ba.AUTH_HEADER] = [""]
        assert not ba.authenticate(hdrs)

        hdrs[ba.AUTH_HEADER] = ["foo"]
        assert not ba.authenticate(hdrs)

        vals = ("foo", "foo", "bar")
        hdrs[ba.AUTH_HEADER] = [http.assemble_http_basic_auth(*vals)]
        assert not ba.authenticate(hdrs)

        ba = http_auth.BasicProxyAuth(http_auth.PassMan(), "test")
        vals = ("basic", "foo", "bar")
        hdrs[ba.AUTH_HEADER] = [http.assemble_http_basic_auth(*vals)]
        assert not ba.authenticate(hdrs)


class Bunch: pass


class TestAuthAction:
    def test_nonanonymous(self):
        m = Bunch()
        aa = http_auth.NonanonymousAuthAction(None, "authenticator")
        aa(None, m, None, None)
        assert m.authenticator  

    def test_singleuser(self):
        m = Bunch()
        aa = http_auth.SingleuserAuthAction(None, "authenticator")
        aa(None, m, "foo:bar", None)
        assert m.authenticator  
        tutils.raises("invalid", aa, None, m, "foo", None)

    def test_httppasswd(self):
        m = Bunch()
        aa = http_auth.HtpasswdAuthAction(None, "authenticator")
        aa(None, m, tutils.test_data.path("data/htpasswd"), None)
        assert m.authenticator  
