class Response(object):

    def __init__(
        self,
        httpversion,
        status_code,
        msg,
        headers,
        content,
        sslinfo=None,
    ):
        self.httpversion = httpversion
        self.status_code = status_code
        self.msg = msg
        self.headers = headers
        self.content = content
        self.sslinfo = sslinfo

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "Response(%s - %s)" % (self.status_code, self.msg)
