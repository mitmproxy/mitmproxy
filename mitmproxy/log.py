from __future__ import annotations

import logging
import os
import typing
import warnings
from dataclasses import dataclass

from mitmproxy import hooks
from mitmproxy.contrib import click as miniclick
from mitmproxy.utils import human

if typing.TYPE_CHECKING:
    from mitmproxy import master

ALERT = logging.INFO + 1
"""
The ALERT logging level has the same urgency as info, but
signals to interactive tools that the user's attention should be
drawn to the output even if they're not currently looking at the
event log.
"""
logging.addLevelName(ALERT, "ALERT")

LogLevels = [
    "error",
    "warn",
    "info",
    "alert",
    "debug",
]

LOG_COLORS = {logging.ERROR: "red", logging.WARNING: "yellow", ALERT: "magenta"}


class MitmFormatter(logging.Formatter):
    def __init__(self, colorize: bool):
        super().__init__()
        self.colorize = colorize
        time = "[%s]"
        client = "[%s]"
        if colorize:
            time = miniclick.style(time, fg="cyan", dim=True)
            client = miniclick.style(client, fg="yellow", dim=True)

        self.with_client = f"{time}{client} %s"
        self.without_client = f"{time} %s"

    default_time_format = "%H:%M:%S"
    default_msec_format = "%s.%03d"

    def format(self, record: logging.LogRecord) -> str:
        time = self.formatTime(record)
        message = record.getMessage()
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        if self.colorize:
            message = miniclick.style(
                message,
                fg=LOG_COLORS.get(record.levelno),
                # dim=(record.levelno <= logging.DEBUG)
            )
        if client := getattr(record, "client", None):
            client = human.format_address(client)
            return self.with_client % (time, client, message)
        else:
            return self.without_client % (time, message)


class MitmLogHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initiated_in_test = os.environ.get("PYTEST_CURRENT_TEST")

    def filter(self, record: logging.LogRecord) -> bool:
        # We can't remove stale handlers here because that would modify .handlers during iteration!
        return bool(
            super().filter(record)
            and (
                not self._initiated_in_test
                or self._initiated_in_test == os.environ.get("PYTEST_CURRENT_TEST")
            )
        )

    def install(self) -> None:
        if self._initiated_in_test:
            for h in list(logging.getLogger().handlers):
                if (
                    isinstance(h, MitmLogHandler)
                    and h._initiated_in_test != self._initiated_in_test
                ):
                    h.uninstall()

        logging.getLogger().addHandler(self)

    def uninstall(self) -> None:
        logging.getLogger().removeHandler(self)


# everything below is deprecated!


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

    Deprecated: Please use the standard Python logging module instead.
    """

    def __init__(self, master):
        self.master = master

    def debug(self, txt):
        """
        Log with level debug.
        """
        warnings.warn(
            "mitmproxy's ctx.log.debug() is deprecated. Please use the standard Python logging module instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        logging.getLogger().debug(txt)

    def info(self, txt):
        """
        Log with level info.
        """
        warnings.warn(
            "mitmproxy's ctx.log.info() is deprecated. Please use the standard Python logging module instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        logging.getLogger().info(txt)

    def alert(self, txt):
        """
        Log with level alert. Alerts have the same urgency as info, but
        signals to interactive tools that the user's attention should be
        drawn to the output even if they're not currently looking at the
        event log.
        """
        warnings.warn(
            "mitmproxy's ctx.log.alert() is deprecated. Please use the standard Python logging module instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        logging.getLogger().log(ALERT, txt)

    def warn(self, txt):
        """
        Log with level warn.
        """
        warnings.warn(
            "mitmproxy's ctx.log.warn() is deprecated. Please use the standard Python logging module instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        logging.getLogger().warning(txt)

    def error(self, txt):
        """
        Log with level error.
        """
        warnings.warn(
            "mitmproxy's ctx.log.error() is deprecated. Please use the standard Python logging module instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        logging.getLogger().error(txt)

    def __call__(self, text, level="info"):
        warnings.warn(
            "mitmproxy's ctx.log() is deprecated. Please use the standard Python logging module instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        logging.getLogger().log(level=logging.getLevelName(level.upper()), msg=text)


LOGGING_LEVELS_TO_LOGENTRY = {
    logging.ERROR: "error",
    logging.WARNING: "warn",
    logging.INFO: "info",
    ALERT: "alert",
    logging.DEBUG: "debug",
}


class LegacyLogEvents(MitmLogHandler):
    """Emit deprecated `add_log` events from stdlib logging."""

    def __init__(
        self,
        master: master.Master,
    ):
        super().__init__()
        self.master = master
        self.formatter = MitmFormatter(colorize=False)

    def emit(self, record: logging.LogRecord) -> None:
        entry = LogEntry(
            msg=self.format(record),
            level=LOGGING_LEVELS_TO_LOGENTRY.get(record.levelno, "error"),
        )
        self.master.event_loop.call_soon_threadsafe(
            self.master.addons.trigger,
            AddLogHook(entry),
        )


@dataclass
class AddLogHook(hooks.Hook):
    """
    **Deprecated:** Starting with mitmproxy 9, users should use the standard Python logging module instead, for example
    by calling `logging.getLogger().addHandler()`.

    Called whenever a new log entry is created through the mitmproxy
    context. Be careful not to log from this event, which will cause an
    infinite loop!
    """

    entry: LogEntry


def log_tier(level):
    """
    Comparison method for "old" LogEntry log tiers.
    Ideally you should use the standard Python logging module instead.
    """
    return dict(error=0, warn=1, info=2, alert=2, debug=3).get(level)
