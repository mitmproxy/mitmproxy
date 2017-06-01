
class LogEntry:
    def __init__(self, msg, level):
        self.msg = msg
        self.level = level

    def __repr__(self):
        return "LogEntry({}, {})".format(self.msg, self.level)


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

    def alert(self, txt):
        """
            Log with level alert. Alerts have the same urgency as info, but
            signals to interctive tools that the user's attention should be
            drawn to the output even if they're not currently looking at the
            event log.
        """
        self(txt, "alert")

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
    return dict(error=0, warn=1, info=2, alert=2, debug=3).get(level)
