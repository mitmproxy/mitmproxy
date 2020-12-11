new_proxy_core = False
"""If true, use mitmproxy's new sans-io proxy core."""

if new_proxy_core:  # pragma: no cover
    from mitmproxy.proxy2 import context

    Client = context.Client  # type: ignore
    Server = context.Server  # type: ignore
else:  # pragma: no cover
    from mitmproxy import connections

    Client = connections.ClientConnection  # type: ignore
    Server = connections.ServerConnection  # type: ignore
