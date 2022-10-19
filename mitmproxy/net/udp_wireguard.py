"""
This module contains a mock DatagramTransport for use with mitmproxy-wireguard.
"""
import asyncio
from typing import Any

import mitmproxy_wireguard as wg

from mitmproxy.connection import Address


class WireGuardDatagramTransport(asyncio.DatagramTransport):
    def __init__(self, server: wg.Server, local_addr: Address, remote_addr: Address):
        self._server: wg.Server = server
        self._local_addr: Address = local_addr
        self._remote_addr: Address = remote_addr
        super().__init__()

    def sendto(self, data, addr=None):
        self._server.send_datagram(data, self._local_addr, addr or self._remote_addr)

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        if name == "sockname":
            return self._server.getsockname()
        else:
            raise NotImplementedError

    def get_protocol(self):
        return self

    async def drain(self) -> None:
        pass

    async def wait_closed(self) -> None:
        pass
