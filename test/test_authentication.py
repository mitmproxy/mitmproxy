import binascii
from libmproxy import authentication
from netlib import odict
import tutils


class TestNullProxyAuth:
    def test_simple(self):
        na = authentication.NullProxyAuth(authentication.PermissivePasswordManager())
        assert not na.auth_challenge_headers()
        assert na.authenticate("foo")
        na.clean({})


class TestBasicProxyAuth:
    def test_simple(self):
        ba = authentication.BasicProxyAuth(authentication.PermissivePasswordManager(), "test")
        h = odict.ODictCaseless()
        assert ba.auth_challenge_headers()
        assert not ba.authenticate(h)

    def test_parse_auth_value(self):
        ba = authentication.BasicProxyAuth(authentication.PermissivePasswordManager(), "test")
        vals = ("basic", "foo", "bar")
        assert ba.parse_auth_value(ba.unparse_auth_value(*vals)) == vals
        tutils.raises(ValueError, ba.parse_auth_value, "")
        tutils.raises(ValueError, ba.parse_auth_value, "foo bar")

        v = "basic " + binascii.b2a_base64("foo")
        tutils.raises(ValueError, ba.parse_auth_value, v)

    def test_authenticate_clean(self):
        ba = authentication.BasicProxyAuth(authentication.PermissivePasswordManager(), "test")

        hdrs = odict.ODictCaseless()
        vals = ("basic", "foo", "bar")
        hdrs[ba.AUTH_HEADER] = [ba.unparse_auth_value(*vals)]
        assert ba.authenticate(hdrs)

        ba.clean(hdrs)
        assert not ba.AUTH_HEADER in hdrs


        hdrs[ba.AUTH_HEADER] = [""]
        assert not ba.authenticate(hdrs)

        hdrs[ba.AUTH_HEADER] = ["foo"]
        assert not ba.authenticate(hdrs)

        vals = ("foo", "foo", "bar")
        hdrs[ba.AUTH_HEADER] = [ba.unparse_auth_value(*vals)]
        assert not ba.authenticate(hdrs)

        ba = authentication.BasicProxyAuth(authentication.PasswordManager(), "test")
        vals = ("basic", "foo", "bar")
        hdrs[ba.AUTH_HEADER] = [ba.unparse_auth_value(*vals)]
        assert not ba.authenticate(hdrs)

