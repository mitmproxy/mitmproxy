import os.path
import typing

import sys

from mitmproxy import ctx
from mitmproxy import io
from mitmproxy import exceptions


class ReadFile:
    """
        An addon that handles reading from file on startup.
    """
    def load_flows(self, fo: typing.IO[bytes]) -> int:
        cnt = 0
        freader = io.FlowReader(fo)
        try:
            for flow in freader.stream():
                ctx.master.load_flow(flow)
                cnt += 1
        except (IOError, exceptions.FlowReadException) as e:
            if cnt:
                ctx.log.warn("Flow file corrupted - loaded %i flows." % cnt)
            else:
                ctx.log.error("Flow file corrupted.")
            raise exceptions.FlowReadException(str(e)) from e
        else:
            return cnt

    def load_flows_from_path(self, path: str) -> int:
        if path == "-":
            return self.load_flows(sys.stdin.buffer)
        else:
            path = os.path.expanduser(path)
            try:
                with open(path, "rb") as f:
                    return self.load_flows(f)
            except IOError as e:
                ctx.log.error("Cannot load flows: {}".format(e))
                raise exceptions.FlowReadException(str(e)) from e

    def running(self):
        if ctx.options.rfile:
            try:
                self.load_flows_from_path(ctx.options.rfile)
            except exceptions.FlowReadException as e:
                raise exceptions.OptionsError(e) from e
            finally:
                ctx.master.addons.trigger("processing_complete")
