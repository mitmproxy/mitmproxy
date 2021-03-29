import ipaddress
from mitmproxy import ctx


class Block:
    def load(self, loader):
        loader.add_option(
            "block_global", bool, True,
            """
            Block connections from public IP addresses.
            """
        )
        loader.add_option(
            "block_private", bool, False,
            """
            Block connections from local (private) IP addresses.
            This option does not affect loopback addresses (connections from the local machine),
            which are always permitted.
            """
        )

    def client_connected(self, client):
        parts = client.peername[0].rsplit("%", 1)
        address = ipaddress.ip_address(parts[0])
        if isinstance(address, ipaddress.IPv6Address):
            address = address.ipv4_mapped or address

        if address.is_loopback:
            return

        if ctx.options.block_private and address.is_private:
            ctx.log.warn(f"Client connection from {client.peername[0]} killed by block_private option.")
            client.error = "Connection killed by block_private."

        if ctx.options.block_global and address.is_global:
            ctx.log.warn(f"Client connection from {client.peername[0]} killed by block_global option.")
            client.error = "Connection killed by block_global."
