import os.path
import typing

from mitmproxy import command
from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import io
from mitmproxy import ctx
from mitmproxy import flow
from mitmproxy import http
import mitmproxy.types
import sys
import errno


class Save:
    def __init__(self):
        self.stream = None
        self.filt = None
        self.active_flows: typing.Set[flow.Flow] = set()

    def load(self, loader):
        loader.add_option(
            "save_stream_file", typing.Optional[str], None,
            "Stream flows to file as they arrive. Prefix path with + to append."
        )
        loader.add_option(
            "save_stream_filter", typing.Optional[str], None,
            "Filter which flows are written to file."
        )

    def open_file(self, path):
        if path.startswith("+"):
            path = path[1:]
            mode = "ab"
        else:
            mode = "wb"
        path = os.path.expanduser(path)
        return open(path, mode)

    def start_stream_to_path(self, path, flt):
        try:
            f = self.open_file(path)
        except OSError as v:
            raise exceptions.OptionsError(str(v))
        self.stream = io.FilteredFlowWriter(f, flt)
        self.active_flows = set()

    def add(self, flow):
        try:
            self.stream.add(flow)
        except OSError as e:
            if e.errno == errno.ENOSPC:
                ctx.log.error("Exiting due to insufficient space on disk")
            else:
                ctx.log.error("Error: {}".format(e))
            sys.exit(1)

    def configure(self, updated):
        # We're already streaming - stop the previous stream and restart
        if "save_stream_filter" in updated:
            if ctx.options.save_stream_filter:
                try:
                    self.filt = flowfilter.parse(ctx.options.save_stream_filter)
                except ValueError as e:
                    raise exceptions.OptionsError(str(e)) from e
            else:
                self.filt = None
        if "save_stream_file" in updated or "save_stream_filter" in updated:
            if self.stream:
                self.done()
            if ctx.options.save_stream_file:
                self.start_stream_to_path(ctx.options.save_stream_file, self.filt)

    @command.command("save.file")
    def save(self, flows: typing.Sequence[flow.Flow], path: mitmproxy.types.Path) -> None:
        """
            Save flows to a file. If the path starts with a +, flows are
            appended to the file, otherwise it is over-written.
        """
        try:
            f = self.open_file(path)
        except OSError as v:
            raise exceptions.CommandError(v) from v
        stream = io.FlowWriter(f)
        for i in flows:
            stream.add(i)
        f.close()
        ctx.log.alert("Saved %s flows." % len(flows))

    def tcp_start(self, flow):
        if self.stream:
            self.active_flows.add(flow)

    def tcp_end(self, flow):
        if self.stream:
            self.add(flow)
            self.active_flows.discard(flow)

    def tcp_error(self, flow):
        self.tcp_end(flow)

    def websocket_end(self, flow: http.HTTPFlow):
        if self.stream:
            self.add(flow)
            self.active_flows.discard(flow)

    def request(self, flow: http.HTTPFlow):
        if self.stream:
            self.active_flows.add(flow)

    def response(self, flow: http.HTTPFlow):
        # websocket flows will receive a websocket_end,
        # we don't want to persist them here already
        if self.stream and flow.websocket is None:
            self.add(flow)
            self.active_flows.discard(flow)

    def error(self, flow: http.HTTPFlow):
        self.response(flow)

    def done(self):
        if self.stream:
            for f in self.active_flows:
                self.stream.add(f)
            self.active_flows = set()
            self.stream.fo.close()
            self.stream = None
