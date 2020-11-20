import abc
import logging
import random
import string
import time
from typing import Dict, List, cast, Any

import mitmproxy.http
from mitmproxy import flowfilter
from mitmproxy import master
from mitmproxy.script import concurrent
from selenium import webdriver

logger = logging.getLogger(__name__)

cookie_key_name = {
    "path": "Path",
    "expires": "Expires",
    "domain": "Domain",
    "is_http_only": "HttpOnly",
    "is_secure": "Secure"
}


def randomString(string_length=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(string_length))


class AuthorizationOracle(abc.ABC):
    """Abstract class for an authorization oracle which decides if a given request or response is authenticated."""

    @abc.abstractmethod
    def is_unauthorized_request(self, flow: mitmproxy.http.HTTPFlow) -> bool:
        pass

    @abc.abstractmethod
    def is_unauthorized_response(self, flow: mitmproxy.http.HTTPFlow) -> bool:
        pass


class SeleniumAddon:
    """ This Addon can be used in combination with web application scanners in order to help them to authenticate
    against a web application.

    Since the authentication is highly dependant on the web application, this add-on includes the abstract method
    *login*. In order to use the add-on, a class for the web application inheriting from SeleniumAddon needs to be
    created. This class needs to include the concrete selenium actions necessary to authenticate against the web
    application. In addition, an authentication oracle which inherits from AuthorizationOracle should be created.
    """

    def __init__(self, fltr: str, domain: str,
                 auth_oracle: AuthorizationOracle):
        self.filter = flowfilter.parse(fltr)
        self.auth_oracle = auth_oracle
        self.domain = domain
        self.browser = None
        self.set_cookies = False

        options = webdriver.FirefoxOptions()
        options.headless = True

        profile = webdriver.FirefoxProfile()
        profile.set_preference('network.proxy.type', 0)
        self.browser = webdriver.Firefox(firefox_profile=profile,
                                         options=options)
        self.cookies: List[Dict[str, str]] = []

    def _login(self, flow):
        self.cookies = self.login(flow)
        self.browser.get("about:blank")
        self._set_request_cookies(flow)
        self.set_cookies = True

    def request(self, flow: mitmproxy.http.HTTPFlow):
        if flow.request.is_replay:
            logger.warning("Caught replayed request: " + str(flow))
        if (not self.filter or self.filter(flow)) and self.auth_oracle.is_unauthorized_request(flow):
            logger.debug("unauthorized request detected, perform login")
            self._login(flow)

    # has to be concurrent because replay.client is blocking and replayed flows
    # will also call response
    @concurrent
    def response(self, flow: mitmproxy.http.HTTPFlow):
        if flow.response and (self.filter is None or self.filter(flow)):
            if self.auth_oracle.is_unauthorized_response(flow):
                self._login(flow)
                new_flow = flow.copy()
                if master and hasattr(master, 'commands'):
                    # cast necessary for mypy
                    cast(Any, master).commands.call("replay.client", [new_flow])
                    count = 0
                    while new_flow.response is None and count < 10:
                        logger.error("waiting since " + str(count) + " ...")
                        count = count + 1
                        time.sleep(1)
                    if new_flow.response:
                        flow.response = new_flow.response
                else:
                    logger.warning("Could not call 'replay.client' command since master was not initialized yet.")

            if self.set_cookies and flow.response:
                logger.debug("set set-cookie header for response")
                self._set_set_cookie_headers(flow)
                self.set_cookies = False

    def done(self):
        self.browser.close()

    def _set_set_cookie_headers(self, flow: mitmproxy.http.HTTPFlow):
        if flow.response and self.cookies:
            for cookie in self.cookies:
                parts = [f"{cookie['name']}={cookie['value']}"]
                for k, v in cookie_key_name.items():
                    if k in cookie and isinstance(cookie[k], str):
                        parts.append(f"{v}={cookie[k]}")
                    elif k in cookie and isinstance(cookie[k], bool) and cookie[k]:
                        parts.append(cookie[k])
                encoded_c = "; ".join(parts)
                flow.response.headers["set-cookie"] = encoded_c

    def _set_request_cookies(self, flow: mitmproxy.http.HTTPFlow):
        if self.cookies:
            cookies = "; ".join(
                map(lambda c: f"{c['name']}={c['value']}", self.cookies))
            flow.request.headers["cookie"] = cookies

    @abc.abstractmethod
    def login(self, flow: mitmproxy.http.HTTPFlow) -> List[Dict[str, str]]:
        pass
