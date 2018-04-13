import asyncio
import os.path
import sys
import typing

from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import io


class ReadFile:
    """
        An addon that handles reading from file on startup.
    """
    def load(self, loader):
        loader.add_option(
            "rfile", typing.Optional[str], None,
            "Read flows from file."
        )

    async def load_flows(self, fo: typing.IO[bytes]) -> int:
        cnt = 0
        freader = io.FlowReader(fo)
        try:
            for flow in freader.stream():
                await ctx.master.load_flow(flow)
                cnt += 1
        except (IOError, exceptions.FlowReadException) as e:
            if cnt:
                ctx.log.warn("Flow file corrupted - loaded %i flows." % cnt)
            else:
                ctx.log.error("Flow file corrupted.")
            raise exceptions.FlowReadException(str(e)) from e
        else:
            return cnt

    async def load_flows_from_path(self, path: str) -> int:
        path = os.path.expanduser(path)
        try:
            with open(path, "rb") as f:
                return await self.load_flows(f)
        except IOError as e:
            ctx.log.error("Cannot load flows: {}".format(e))
            raise exceptions.FlowReadException(str(e)) from e

    async def doread(self, rfile):
        try:
            await self.load_flows_from_path(ctx.options.rfile)
        except exceptions.FlowReadException as e:
            raise exceptions.OptionsError(e) from e
        finally:
            ctx.master.addons.trigger("processing_complete")

    def running(self):
        if ctx.options.rfile:
            asyncio.get_event_loop().create_task(self.doread(ctx.options.rfile))


class ReadFileStdin(ReadFile):
    """Support the special case of "-" for reading from stdin"""
    async def load_flows_from_path(self, path: str) -> int:
        if path == "-":
            return await self.load_flows(sys.stdin.buffer)
        else:
            return await super().load_flows_from_path(path)
