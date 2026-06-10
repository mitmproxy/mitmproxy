import asyncio
import logging
import sys

from mitmproxy import ctx
from mitmproxy import log
from mitmproxy.contrib import click as miniclick
from mitmproxy.utils import vt_codes


def _resolve_color_override(raw: object) -> vt_codes.ColorOverride:
    """Coerce the raw ``termlog_colors`` option value into a known literal.

    Defaults to ``"auto"`` for any unexpected value so the type narrows to
    ``vt_codes.ColorOverride`` without requiring callers to validate.
    """
    if raw == "always":
        return "always"
    if raw == "never":
        return "never"
    return "auto"


class ErrorCheck:
    """Monitor startup for error log entries, and terminate immediately if there are some."""

    repeat_errors_on_stderr: bool
    """
    Repeat all errors on stderr before exiting.
    This is useful for the console UI, which otherwise swallows all output.
    """

    def __init__(self, repeat_errors_on_stderr: bool = False) -> None:
        self.repeat_errors_on_stderr = repeat_errors_on_stderr

        self.logger = ErrorCheckHandler()
        self.logger.install()

    def finish(self):
        self.logger.uninstall()

    async def shutdown_if_errored(self):
        # don't run immediately, wait for all logging tasks to finish.
        await asyncio.sleep(0)
        if self.logger.has_errored:
            plural = "s" if len(self.logger.has_errored) > 1 else ""
            if self.repeat_errors_on_stderr:
                message = f"Error{plural} logged during startup:"
                # `ctx.options` may not be loaded yet if errorcheck fires
                # before option registration; default to "auto" in that case.
                opts = getattr(ctx, "options", None)
                color_override = _resolve_color_override(
                    getattr(opts, "termlog_colors", "auto") if opts else "auto"
                )
                if vt_codes.ensure_supported(
                    sys.stderr, override=color_override
                ):  # pragma: no cover
                    message = miniclick.style(message, fg="red")
                details = "\n".join(
                    self.logger.format(r) for r in self.logger.has_errored
                )
                print(f"{message}\n{details}", file=sys.stderr)
            else:
                print(
                    f"Error{plural} logged during startup, exiting...", file=sys.stderr
                )

            sys.exit(1)


class ErrorCheckHandler(log.MitmLogHandler):
    def __init__(self) -> None:
        super().__init__(logging.ERROR)
        self.has_errored: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.has_errored.append(record)
