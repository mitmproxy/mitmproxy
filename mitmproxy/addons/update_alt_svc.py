from mitmproxy.http import HTTPFlow
import re
from mitmproxy import ctx
from mitmproxy.proxy import mode_specs

ALT_SVC = 'alt-svc'
PORT_PATTERN = r'(?<=:)\d{1,5}(?=")'


def update_alt_svc_port(data: str, port: int) -> str:
    return re.sub(PORT_PATTERN, f'{port}', data)


class UpdateAltSvc:
    def load(self, loader):
        loader.add_option("update_alt_svc", bool, True, "Update the ports in alt-svc header to the port that we are listening on in reverse mode")

    def responseheaders(self, flow: HTTPFlow):
        if ctx.options.update_alt_svc and isinstance(flow.client_conn.proxy_mode, mode_specs.ReverseMode):
            listen_port = flow.client_conn.sockname[1]
            headers = flow.response.headers
            if ALT_SVC in headers:
                headers[ALT_SVC] = update_alt_svc_port(headers[ALT_SVC], listen_port)
