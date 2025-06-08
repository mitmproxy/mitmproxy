from __future__ import annotations

import os.path
import secrets

import tornado.web
import tornado.websocket

import mitmproxy.flow
import mitmproxy.tools.web.master
from mitmproxy.tools.web.app import handlers, GZipContentAndFlowFiles
from mitmproxy.tools.web.webaddons import WebAuth


class Application(tornado.web.Application):
    master: mitmproxy.tools.web.master.WebMaster

    def __init__(
        self, master: mitmproxy.tools.web.master.WebMaster, debug: bool
    ) -> None:
        self.master = master
        auth_addon: WebAuth = master.addons.get("webauth")
        super().__init__(
            handlers=handlers,  # type: ignore  # https://github.com/tornadoweb/tornado/pull/3455
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "dist"),
            xsrf_cookies=True,
            xsrf_cookie_kwargs=dict(httponly=True, samesite="Strict"),
            cookie_secret=secrets.token_bytes(32),
            debug=debug,
            autoreload=False,
            transforms=[GZipContentAndFlowFiles],
            is_valid_password=auth_addon.is_valid_password,
            auth_cookie_name=f"mitmproxy-auth-{master.options.web_port}",
        )
