from __future__ import annotations

import hmac
import logging
import secrets
import webbrowser
from collections.abc import Sequence
from typing import TYPE_CHECKING

import argon2

from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy.tools.web.web_columns import AVAILABLE_WEB_COLUMNS

if TYPE_CHECKING:
    from mitmproxy.tools.web.master import WebMaster

logger = logging.getLogger(__name__)


class WebAuth:
    _password: str
    _hasher: argon2.PasswordHasher

    def __init__(self):
        self._password = secrets.token_hex(16)
        self._hasher = argon2.PasswordHasher()

    def load(self, loader):
        loader.add_option(
            "web_password",
            str,
            "",
            "Password to protect the mitmweb user interface. "
            "Values starting with `$` are interpreted as an argon2 hash, "
            "everything else is considered a plaintext password. "
            "If no password is provided, a random token is generated on startup."
            "For automated calls, you can pass the password as token query parameter"
            "or as `Authorization: Bearer ...` header.",
        )

    def configure(self, updated) -> None:
        if "web_password" in updated:
            if ctx.options.web_password.startswith("$"):
                try:
                    argon2.extract_parameters(ctx.options.web_password)
                except argon2.exceptions.InvalidHashError:
                    raise exceptions.OptionsError(
                        "`web_password` starts with `$`, but it's not a valid argon2 hash."
                    )
            elif ctx.options.web_password:
                logger.warning(
                    "Using a plaintext password to protect the mitmweb user interface. "
                    "Consider using an argon2 hash for `web_password`  instead."
                )
            self._password = ctx.options.web_password or secrets.token_hex(16)

    @property
    def web_url(self) -> str:
        if ctx.options.web_password:
            auth = ""  # We don't want to print plaintext passwords (and it doesn't work for argon2 anyhow).
        else:
            auth = f"?token={self._password}"
        # noinspection HttpUrlsUsage
        return f"http://{ctx.options.web_host}:{ctx.options.web_port}/{auth}"

    @staticmethod
    def auth_cookie_name() -> str:
        return f"mitmproxy-auth-{ctx.options.web_port}"

    def is_valid_password(self, password: str) -> bool:
        if self._password.startswith("$"):
            try:
                return self._hasher.verify(self._password, password)
            except argon2.exceptions.VerificationError:
                return False
        else:
            return hmac.compare_digest(
                self._password,
                password,
            )


class WebAddon:
    def load(self, loader):
        loader.add_option("web_open_browser", bool, True, "Start a browser.")
        loader.add_option("web_debug", bool, False, "Enable mitmweb debugging.")
        loader.add_option("web_port", int, 8081, "Web UI port.")
        loader.add_option("web_host", str, "127.0.0.1", "Web UI host.")
        loader.add_option(
            "web_columns",
            Sequence[str],
            ["tls", "icon", "path", "method", "status", "size", "time"],
            f"Columns to show in the flow list. Can be one of the following: {', '.join(AVAILABLE_WEB_COLUMNS)}",
        )

    def running(self):
        if hasattr(ctx.options, "web_open_browser") and ctx.options.web_open_browser:
            master: WebMaster = ctx.master  # type: ignore
            success = open_browser(master.web_url)
            if not success:
                logger.info(
                    f"No web browser found. Please open a browser and point it to {master.web_url}",
                )
            if not success and not ctx.options.web_password:
                logger.info(
                    f"You can configure a fixed authentication token by setting the `web_password` option "
                    f"(https://docs.mitmproxy.org/stable/concepts-options/#web_password).",
                )


def open_browser(url: str) -> bool:
    """
    Open a URL in a browser window.
    In contrast to webbrowser.open, we limit the list of suitable browsers.
    This gracefully degrades to a no-op on headless servers, where webbrowser.open
    would otherwise open lynx.

    Returns:
        True, if a browser has been opened
        False, if no suitable browser has been found.
    """
    browsers = (
        "windows-default",
        "macosx",
        "wslview %s",
        "gio",
        "x-www-browser",
        "gnome-open %s",
        "xdg-open",
        "google-chrome",
        "chrome",
        "chromium",
        "chromium-browser",
        "firefox",
        "opera",
        "safari",
    )
    for browser in browsers:
        try:
            b = webbrowser.get(browser)
        except webbrowser.Error:
            pass
        else:
            if b.open(url):
                return True
    return False
