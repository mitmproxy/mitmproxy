class RenderError(Exception):
    pass


class FileAccessDenied(RenderError):
    pass


class ParseException(Exception):

    def __init__(self, msg, s, col):
        Exception.__init__(self)
        self.msg = msg
        self.s = s
        self.col = col

    def marked(self):
        return "%s\n%s" % (self.s, " " * (self.col - 1) + "^")

    def __str__(self):
        return "%s at char %s" % (self.msg, self.col)
