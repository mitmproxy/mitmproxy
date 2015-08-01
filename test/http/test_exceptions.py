from netlib.http.exceptions import *

def test_HttpAuthenticationError():
    x = HttpAuthenticationError({"foo": "bar"})
    assert str(x)
    assert "foo" in x.headers
