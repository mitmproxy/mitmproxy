from __future__ import annotations

import os.path
import secrets

import tornado.web
import tornado.websocket

import mitmproxy.flow
import mitmproxy.tools.webnext.master
from mitmproxy.tools.web.app import GZipContentAndFlowFiles
from mitmproxy.tools.web.app import handlers
from mitmproxy.tools.web.webaddons import WebAuth


class Application(tornado.web.Application):
    master: mitmproxy.tools.webnext.master.WebMaster

    def __init__(
        self, master: mitmproxy.tools.webnext.master.WebMaster, debug: bool
    ) -> None:
        self.master = master
        auth_addon: WebAuth = master.addons.get("webauth")
        # The option to disable XSRF cookies is needed to test actions like replay requests from the vite dev server during development.
        # In all other scenarios this should be turned ON, hence the warning.
        disable_xsrf_cookies = os.environ.get("UNSAFE_DISABLE_XSRF_COOKIES", False)
        if disable_xsrf_cookies:
            print(
                "WARNING: XSRF cookies are disabled! This is unsafe and should only be used for development purposes."
            )
        super().__init__(
            handlers=handlers,  # type: ignore  # https://github.com/tornadoweb/tornado/pull/3455
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "dist"),
            xsrf_cookies=not disable_xsrf_cookies,
            xsrf_cookie_kwargs=dict(httponly=True, samesite="Strict"),
            cookie_secret=secrets.token_bytes(32),
            debug=debug,
            autoreload=False,
            transforms=[GZipContentAndFlowFiles],
            is_valid_password=auth_addon.is_valid_password,
            auth_cookie_name=f"mitmproxy-auth-{master.options.web_port}",
        )
