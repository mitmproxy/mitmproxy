import asyncio
from dataclasses import dataclass

from mitmproxy import hooks


class LogEntry:
    def __init__(self, msg, level):
        # it's important that we serialize to string here already so that we don't pick up changes
        # happening after this log statement.
        self.msg = str(msg)
        self.level = level

    def __eq__(self, other):
        if isinstance(other, LogEntry):
            return self.__dict__ == other.__dict__
        return False

    def __repr__(self):
        return f"LogEntry({self.msg}, {self.level})"


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
            signals to interactive tools that the user's attention should be
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
        asyncio.get_event_loop().call_soon(
            self.master.addons.trigger, AddLogHook(LogEntry(text, level)),
        )


@dataclass
class AddLogHook(hooks.Hook):
    """
    Called whenever a new log entry is created through the mitmproxy
    context. Be careful not to log from this event, which will cause an
    infinite loop!
    """
    entry: LogEntry


LogTierOrder = [
    "error",
    "warn",
    "info",
    "alert",
    "debug",
]


def log_tier(level):
    return dict(error=0, warn=1, info=2, alert=2, debug=3).get(level)
