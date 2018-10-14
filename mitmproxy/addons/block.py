import ipaddress
from mitmproxy import ctx


class Block:
    def load(self, loader):
        loader.add_option(
            "block_global", bool, True,
            """
            Block connections from globally reachable networks, as defined in
            the IANA special purpose registries.
            """
        )
        loader.add_option(
            "block_private", bool, False,
            """
            Block connections from private networks, as defined in the IANA
            special purpose registries. This option does not affect loopback
            addresses.
            """
        )

    def clientconnect(self, layer):
        astr = layer.client_conn.address[0]

        parts = astr.rsplit("%", 1)
        address = ipaddress.ip_address(parts[0])
        if isinstance(address, ipaddress.IPv6Address):
            address = address.ipv4_mapped or address

        if address.is_loopback:
            return

        if ctx.options.block_private and address.is_private:
            ctx.log.warn("Client connection from %s killed by block_private" % astr)
            layer.reply.kill()
        if ctx.options.block_global and address.is_global:
            ctx.log.warn("Client connection from %s killed by block_global" % astr)
            layer.reply.kill()