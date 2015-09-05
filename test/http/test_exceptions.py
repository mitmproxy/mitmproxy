from netlib.http.exceptions import *

class TestHttpError:
    def test_simple(self):
        e = HttpError(404, "Not found")
        assert str(e)
