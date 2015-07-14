class HttpError(Exception):

    def __init__(self, code, message):
        super(HttpError, self).__init__(message)
        self.code = code


class HttpErrorConnClosed(HttpError):
    pass
