from libmproxy import authentication
from netlib import odict


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

