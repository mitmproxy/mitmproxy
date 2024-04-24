import asyncio
import logging
import os.path
import sys
from typing import BinaryIO
from typing import Optional

from mitmproxy import command
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import io

logger = logging.getLogger(__name__)


class ReadFile:
    """
    An addon that handles reading from file on startup.
    """

    def __init__(self):
        self.filter = None
        self._read_task: asyncio.Task | None = None

    def load(self, loader):
        loader.add_option("rfile", Optional[str], None, "Read flows from file.")
        loader.add_option(
            "readfile_filter", Optional[str], None, "Read only matching flows."
        )

    def configure(self, updated):
        if "readfile_filter" in updated:
            if ctx.options.readfile_filter:
                try:
                    self.filter = flowfilter.parse(ctx.options.readfile_filter)
                except ValueError as e:
                    raise exceptions.OptionsError(str(e)) from e
            else:
                self.filter = None

    async def load_flows(self, fo: BinaryIO) -> int:
        cnt = 0
        freader = io.FlowReader(fo)
        try:
            for flow in freader.stream():
                if self.filter and not self.filter(flow):
                    continue
                await ctx.master.load_flow(flow)
                cnt += 1
        except (OSError, exceptions.FlowReadException) as e:
            if cnt:
                logging.warning("Flow file corrupted - loaded %i flows." % cnt)
            else:
                logging.error("Flow file corrupted.")
            raise exceptions.FlowReadException(str(e)) from e
        else:
            return cnt

    async def load_flows_from_path(self, path: str) -> int:
        path = os.path.expanduser(path)
        try:
            with open(path, "rb") as f:
                return await self.load_flows(f)
        except OSError as e:
            logging.error(f"Cannot load flows: {e}")
            raise exceptions.FlowReadException(str(e)) from e

    async def doread(self, rfile: str) -> None:
        try:
            await self.load_flows_from_path(rfile)
        except exceptions.FlowReadException as e:
            logger.exception(f"Failed to read {ctx.options.rfile}: {e}")

    def running(self):
        if ctx.options.rfile:
            self._read_task = asyncio.create_task(self.doread(ctx.options.rfile))

    @command.command("readfile.reading")
    def reading(self) -> bool:
        return bool(self._read_task and not self._read_task.done())


class ReadFileStdin(ReadFile):
    """Support the special case of "-" for reading from stdin"""

    async def load_flows_from_path(self, path: str) -> int:
        if path == "-":  # pragma: no cover
            # Need to think about how to test this. This function is scheduled
            # onto the event loop, where a sys.stdin mock has no effect.
            return await self.load_flows(sys.stdin.buffer)
        else:
            return await super().load_flows_from_path(path)
