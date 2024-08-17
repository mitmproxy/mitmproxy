import re

from mitmproxy import ctx
from mitmproxy.http import HTTPFlow
from mitmproxy.proxy import mode_specs

ALT_SVC = "alt-svc"
HOST_PATTERN = r"([a-zA-Z0-9.-]*:\d{1,5})"


def update_alt_svc_header(header: str, port: int) -> str:
    return re.sub(HOST_PATTERN, f":{port}", header)


class UpdateAltSvc:
    def load(self, loader):
        loader.add_option(
            "keep_alt_svc_header",
            bool,
            False,
            "Reverse Proxy: Keep Alt-Svc headers as-is, even if they do not point to mitmproxy. Enabling this option may cause clients to bypass the proxy.",
        )

    def responseheaders(self, flow: HTTPFlow):
        assert flow.response
        if (
            not ctx.options.keep_alt_svc_header
            and isinstance(flow.client_conn.proxy_mode, mode_specs.ReverseMode)
            and ALT_SVC in flow.response.headers
        ):
            _, listen_port, *_ = flow.client_conn.sockname
            headers = flow.response.headers
            headers[ALT_SVC] = update_alt_svc_header(headers[ALT_SVC], listen_port)
