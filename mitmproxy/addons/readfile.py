import os.path

from mitmproxy import ctx
from mitmproxy import io
from mitmproxy import exceptions


class ReadFile:
    """
        An addon that handles reading from file on startup.
    """
    def __init__(self):
        self.path = None

    def load_flows_file(self, path: str) -> int:
        path = os.path.expanduser(path)
        cnt = 0
        try:
            with open(path, "rb") as f:
                freader = io.FlowReader(f)
                for i in freader.stream():
                    cnt += 1
                    ctx.master.load_flow(i)
                return cnt
        except (IOError, exceptions.FlowReadException) as v:
            if cnt:
                ctx.log.warn(
                    "Flow file corrupted - loaded %i flows." % cnt,
                )
            else:
                ctx.log.error("Flow file corrupted.")
            raise exceptions.FlowReadException(v)

    def configure(self, options, updated):
        if "rfile" in updated and options.rfile:
            self.path = options.rfile

    def running(self):
        if self.path:
            try:
                self.load_flows_file(self.path)
            except exceptions.FlowReadException as v:
                raise exceptions.OptionsError(v)
            finally:
                self.path = None
                ctx.master.addons.trigger("processing_complete")
