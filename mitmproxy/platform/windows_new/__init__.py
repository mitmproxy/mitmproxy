from __future__ import annotations
import asyncio
from pathlib import Path

from mitmproxy.connection import Address

here = Path(__file__).absolute().parent


class _OsProxy:
    _process: asyncio.subprocess.Process | None = None

    async def start(self, port: int) -> None:
        if self._process is None:
            self._process = await asyncio.create_subprocess_exec(
                here / "launcher.exe", here / "mitmproxy-redirector.exe", str(port),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
            )

    async def resolve(self, addr: Address) -> tuple[Address, Address]:
        assert self._process
        assert self._process.stdin
        assert self._process.stdout
        self._process.stdin.write(f"{addr[0]}:{addr[1]}\n".encode())
        await self._process.stdin.drain()
        original_dst = await self._process.stdout.readline()

        src_host_b, src_port_b, dst_host_b, dst_port_b = original_dst.strip().split(b" ")
        src_host = src_host_b.decode()
        src_port = int(src_port_b)
        dst_host = dst_host_b.decode()
        dst_port = int(dst_port_b)
        return (src_host, src_port), (dst_host, dst_port)

    async def stop(self):
        raise NotImplementedError


os_proxy = _OsProxy()
