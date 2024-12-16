"""
Mitmproxy add-on to support using a PAC file to determine the upstream proxy to use.
Supports adding an alternate proxy to use for when the PAC decides the connection should be DIRECT.
Adds two options to mitmproxy:

pac_url - an url that will return a pac file to use for evaluating which upstream proxy to use.
direct_upstream_proxy - an alternate proxy to be used if the PAC returns DIRECT.

Requires pypac to be installed and available on the python path.

This class is inspired by the user contributed add-on:
https://github.com/mitmproxy/mitmproxy/blob/main/examples/contrib/change_upstream_proxy.py
"""

import logging

import pypac

from mitmproxy import ctx
from mitmproxy import http
from mitmproxy.net import server_spec


class UpstreamPac:
    pac_file: pypac.parser.PACFile | None

    @staticmethod
    def load(loader) -> None:
        loader.add_option(
            name="direct_upstream_proxy",
            typespec=str | None,
            default=None,
            help="Alternate upstream proxy to use when PAC resolution returns direct (http://localhost:8081)",
        )

        loader.add_option(
            name="pac_url",
            typespec=str | None,
            default=None,
            help="Proxy autoconfig url used to retrieve the PAC file",
        )

    @staticmethod
    def configure(updated) -> None:
        if "pac_url" in updated:
            if ctx.options.pac_url is None:
                UpstreamPac.pac_file = None
                logging.info("No pac file specified")
            else:
                UpstreamPac.pac_file = pypac.get_pac(
                    url=ctx.options.pac_url,
                    allowed_content_types=[
                        "application/x-ns-proxy-autoconfig ",
                        "application/x-javascript-config",
                        "text/html",
                        "text/plain",
                    ],
                )
                if UpstreamPac.pac_file is None:
                    logging.error(
                        "Failed to load pac file from: %s", ctx.options.pac_url
                    )

    @staticmethod
    def proxy_address(flow: http.HTTPFlow) -> tuple[str, tuple[str, int]] | None:
        if UpstreamPac.pac_file:
            proxy = UpstreamPac.pac_file.find_proxy_for_url(
                flow.request.url, flow.request.host
            )

            if proxy == "DIRECT":
                if ctx.options.direct_upstream_proxy is not None:
                    return server_spec.parse(ctx.options.direct_upstream_proxy, "http")
                else:
                    return None
            else:
                proxy_url = pypac.parser.proxy_url(proxy)
                return server_spec.parse(proxy_url, "http")
        return None

    @staticmethod
    def request(flow: http.HTTPFlow) -> None:
        address = UpstreamPac.proxy_address(flow)

        if address is not None:
            logging.info(
                "Using proxy %s://%s:%s for %s"
                % (address[0], address[1][0], address[1][1], flow.request.host)
            )
            flow.server_conn.via = address


addons = [UpstreamPac()]
