import binascii
from libmproxy import authentication
from netlib import odict
import tutils


class TestNullProxyAuth:
    def test_simple(self):
        na = authentication.NullProxyAuth(authentication.PermissivePasswordManager())
        assert not na.auth_challenge_headers()
        assert na.authenticate("foo")


class TestBasicProxyAuth:
    def test_simple(self):
        ba = authentication.BasicProxyAuth(authentication.PermissivePasswordManager())
        h = odict.ODictCaseless()
        assert ba.auth_challenge_headers()
        assert not ba.authenticate(h)

    def test_parse_auth_value(self):
        ba = authentication.BasicProxyAuth(authentication.PermissivePasswordManager())
        vals = ("basic", "foo", "bar")
        assert ba.parse_auth_value(ba.unparse_auth_value(*vals)) == vals
        tutils.raises(ValueError, ba.parse_auth_value, "")
        tutils.raises(ValueError, ba.parse_auth_value, "foo bar")

        v = "basic " + binascii.b2a_base64("foo")
        tutils.raises(ValueError, ba.parse_auth_value, v)

