import falcon

from mitmproxy import ctx
from typing import Sequence


class HealthCheckResource:
    def addon_path(self):
        return "healthcheck"

    def apispec(self, spec):
        spec.path(resource=self)

    def on_get(self, req, resp):
        """Gets the Healthcheck.
        ---
        description: Get the healthcheck
        tags:
            - BrowserUpProxy
        responses:
            200:
                description: OK means all is well.
        """
        resp.body = 'OK'
        resp.status = falcon.HTTP_200

class ProxyManagerAddOn:

    def load(self, loader):
        loader.add_option(
            name = "addheader",
            typespec = bool,
            default = False,
            help = "Add a count header to responses",
        )
        loader.add_option(
            name="dns_resolving_delay_ms",
            typespec=int,
            default=False,
            help="Delay DNS resolution by milliseconds"
        )
        loader.add_option(
            name="upstream_proxy_credentials",
            typespec=str,
            default="",
            help="Upstream proxy credentials"
        )
        loader.add_option(
            name="upstream_proxy_exception_hosts",
            typespec=Sequence[str],
            default=[],
            help="Upstream proxy credentials"
        )

    def get_resources(self):
        return [HealthCheckResource()]

    def http_connect(self, f):
        if ctx.options.upstream_proxy_credentials and f.mode == "upstream":
            f.request.headers["Proxy-Authorization"] = "Basic " + ctx.options.upstream_proxy_credentials

    def requestheaders(self, f):
        if self.are_upstream_proxy_credentials_available():
            if f.mode == "upstream" and not f.server_conn.via:
                f.request.headers["Proxy-Authorization"] = "Basic " + ctx.options.upstream_proxy_credentials
            elif ctx.options.mode.startswith("reverse"):
                f.request.headers["Proxy-Authorization"] = "Basic " + ctx.options.upstream_proxy_credentials

    def response_from_upstream_proxy(self, f):
        if self.are_upstream_proxy_credentials_available() and f.response is not None and f.response.status_code == 407:
            f.response.status_code = 502

    def are_upstream_proxy_credentials_available(self):
        return ctx.options.upstream_proxy_credentials is not None and ctx.options.upstream_proxy_credentials != ""

addons = [
    ProxyManagerAddOn()
]