from netlib import odict

class HttpError(Exception):
    def __init__(self, code, message):
        super(HttpError, self).__init__(message)
        self.code = code


class HttpErrorConnClosed(HttpError):
    pass


class HttpAuthenticationError(Exception):
    def __init__(self, auth_headers=None):
        super(HttpAuthenticationError, self).__init__(
            "Proxy Authentication Required"
        )
        if isinstance(auth_headers, dict):
            auth_headers = odict.ODictCaseless(auth_headers.items())
        self.headers = auth_headers
        self.code = 407

    def __repr__(self):
        return "Proxy Authentication Required"
