
class LogEntry:
    def __init__(self, msg, level):
        self.msg = msg
        self.level = level


class Log:
    """
        The central logger, exposed to scripts as mitmproxy.ctx.log.
    """
    def __init__(self, master):
        self.master = master

    def debug(self, txt):
        """
            Log with level debug.
        """
        self(txt, "debug")

    def info(self, txt):
        """
            Log with level info.
        """
        self(txt, "info")

    def warn(self, txt):
        """
            Log with level warn.
        """
        self(txt, "warn")

    def error(self, txt):
        """
            Log with level error.
        """
        self(txt, "error")

    def __call__(self, text, level="info"):
        self.master.add_log(text, level)


def log_tier(level):
    return dict(error=0, warn=1, info=2, debug=3).get(level)
