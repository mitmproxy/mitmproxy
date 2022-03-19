
import asyncio
from typing import Tuple


class UdpServer(asyncio.AbstractServer):
    pass


async def start_server(client_connected_cb, host: str, port: int) -> UdpServer:
    pass


async def open_connection(host: str, port: int) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    pass