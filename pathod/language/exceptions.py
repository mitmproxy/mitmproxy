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
        return "{}\n{}".format(self.s, " " * (self.col - 1) + "^")

    def __str__(self):
        return f"{self.msg} at char {self.col}"
