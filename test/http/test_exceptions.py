from netlib.http.exceptions import *
from netlib import odict

class TestHttpError:
    def test_simple(self):
        e = HttpError(404, "Not found")
        assert str(e)

class TestHttpAuthenticationError:
    def test_init(self):
        headers = odict.ODictCaseless([("foo", "bar")])
        x = HttpAuthenticationError(headers)
        assert str(x)
        assert isinstance(x.headers, odict.ODictCaseless)
        assert x.code == 407
        assert x.headers == headers
        print(x.headers.keys())
        assert "foo" in x.headers.keys()

    def test_header_conversion(self):
        headers = {"foo": "bar"}
        x = HttpAuthenticationError(headers)
        assert isinstance(x.headers, odict.ODictCaseless)
        assert x.headers.lst == headers.items()

    def test_repr(self):
        assert repr(HttpAuthenticationError()) == "Proxy Authentication Required"
