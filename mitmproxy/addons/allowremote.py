import ipaddress
from mitmproxy import ctx


class AllowRemote:
    def load(self, loader):
        loader.add_option(
            "allow_remote", bool, False,
            """
            Allow remote clients to connect to proxy. If set to false,
            client will not be able to connect to proxy unless it is on the same network
            or the proxyauth option is set
            """
        )

    def clientconnect(self, layer):
        address = layer.client_conn.address

        accept_connection = (
            ctx.options.allow_remote or
            ipaddress.ip_address(address[0]).is_private or
            ctx.options.proxyauth is not None
        )

        if not accept_connection:
            layer.reply.kill()
            ctx.log.warn("Client connection was killed because allow_remote option is set to false, "
                         "client IP was not a private IP and proxyauth was not set.\n"
                         "To allow remote connections set allow_remote option to true or set proxyauth option.")
