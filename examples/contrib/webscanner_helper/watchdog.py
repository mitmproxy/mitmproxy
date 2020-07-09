import pathlib
import time
import typing
import logging
from datetime import datetime

import mitmproxy.connections
import mitmproxy.http
from mitmproxy.addons.export import curl_command, raw
from mitmproxy.exceptions import HttpSyntaxException

logger = logging.getLogger(__name__)


class WatchdogAddon():
    """ The Watchdog Add-on can be used in combination with web application scanners in oder to check if the device
        under test responds correctls to the scanner's responses.

    The Watchdog Add-on checks if the device under test responds correctly to the scanner's responses.
    If the Watchdog sees that the DUT is no longer responding correctly, an multiprocessing event is set.
    This information can be used to restart the device under test if necessary.
    """

    def __init__(self, event, outdir: pathlib.Path, timeout=None):
        """Initializes the Watchdog.

        Args:
            event: multiprocessing.Event that will be set if the watchdog is triggered.
            outdir: path to a directory in which the triggering requests will be saved (curl and raw).
            timeout_conn: float that specifies the timeout for the server connection
        """
        self.error_event = event
        self.flow_dir = outdir
        if self.flow_dir.exists() and not self.flow_dir.is_dir():
            raise RuntimeError("Watchtdog output path must be a directory.")
        elif not self.flow_dir.exists():
            self.flow_dir.mkdir(parents=True)
        self.last_trigger: typing.Union[None, float] = None
        self.timeout: typing.Union[None, float] = timeout

    def serverconnect(self, conn: mitmproxy.connections.ServerConnection):
        if self.timeout is not None:
            conn.settimeout(self.timeout)

    @classmethod
    def not_in_timeout(cls, last_triggered, timeout):
        """Checks if current error lies not in timeout after last trigger (potential reset of connection)."""
        return last_triggered is None or timeout is None or (time.time() - last_triggered > timeout)

    def error(self, flow):
        """ Checks if the watchdog will be triggered.

        Only triggers watchdog for timeouts after last reset and if flow.error is set (shows that error is a server
        error). Ignores HttpSyntaxException Errors since this can be triggered on purpose by web application scanner.

        Args:
            flow: mitmproxy.http.flow
        """
        if (self.not_in_timeout(self.last_trigger, self.timeout)
                and flow.error is not None and not isinstance(flow.error, HttpSyntaxException)):

            self.last_trigger = time.time()
            logger.error(f"Watchdog triggered! Cause: {flow}")
            self.error_event.set()

            # save the request which might have caused the problem
            if flow.request:
                with (self.flow_dir / f"{datetime.utcnow().isoformat()}.curl").open("w") as f:
                    f.write(curl_command(flow))
                with (self.flow_dir / f"{datetime.utcnow().isoformat()}.raw").open("wb") as f:
                    f.write(raw(flow))
