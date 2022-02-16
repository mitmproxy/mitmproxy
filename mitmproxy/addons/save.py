from datetime import datetime
from pathlib import Path
from sys import exit
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


class Save:
    def __init__(self):
        self.stream = None
        self.path = None
        self.mode = None
        self.filt = None
        self.active_flows: typing.Set[flow.Flow] = set()
        self.curpath = None

    def load(self, loader):
        loader.add_option(
            "save_stream_file", typing.Optional[str], None,
            """
            Stream flows to file as they arrive. Prefix path with + to append.
            The full path can use python strftime() formating, missing
            directories are created as needed. A new file is opened every the
            formatted string changes.
            """
        )
        loader.add_option(
            "save_stream_filter", typing.Optional[str], None,
            "Filter which flows are written to file."
        )

    def prep_path(self, path):
        if path.startswith("+"):
            path = path[1:]
            mode = "ab"
        else:
            mode = "wb"
        path = os.path.expanduser(path)
        return path, mode

    def new_path(self):
        path = datetime.today().strftime(self.path)
        if self.curpath and self.curpath == path:
            return False
        self.curpath = path

        try:
            parent = Path(self.curpath).parent
            if not parent.exists():  # pragma: no cover
                parent.mkdir(parents=True, exist_ok=True)
        except OSError as v:  # pragma: no cover
            ctx.log.error(f"Error while creating directories {parent}: {v}")
        return True

    def new_stream(self):
        if self.new_path():  # pragma: no cover
            if self.stream:
                self.close_stream()
            try:
                f = open(self.curpath, self.mode)
                self.stream = io.FilteredFlowWriter(f, self.filt)
            except OSError as v:
                ctx.log.error(f"Error while opening {self.curpath}: {v}")
                sys.exit(1)
        return self.stream

    def save_flow(self, flow: http.HTTPFlow):
        try:
            self.stream.add(flow)
        except OSError as v:
            ctx.log.error(f"Error while writing to {self.curpath}: {v}")
            sys.exit(1)

    def close_stream(self):
        try:
            self.active_flows = set()
            self.stream.fo.close()
        except OSError as v:
            ctx.log.error(f"Error while closing stream file: {v}")
            sys.exit(1)

    def start_stream_to_path(self, path, flt):
        try:
            self.path, self.mode = self.prep_path(path)
            self.new_path()
            f = open(self.curpath, self.mode)
        except OSError as v:
            raise exceptions.OptionsError(str(v))
        self.stream = io.FilteredFlowWriter(f, flt)
        self.active_flows = set()

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
            path, mode = self.prep_path(path)
            f = open(path, mode)
            stream = io.FlowWriter(f)
            for i in flows:
                stream.add(i)
            f.close()
        except OSError as v:
            raise exceptions.CommandError(v) from v
        ctx.log.alert("Saved %s flows." % len(flows))

    def tcp_start(self, flow):
        if self.stream:
            self.active_flows.add(flow)

    def tcp_end(self, flow):
        if self.stream and self.new_stream():
            self.save_flow(flow)
            self.active_flows.discard(flow)

    def tcp_error(self, flow):
        self.tcp_end(flow)

    def websocket_end(self, flow: http.HTTPFlow):
        if self.stream and self.new_stream():
            self.save_flow(flow)
            self.active_flows.discard(flow)

    def request(self, flow: http.HTTPFlow):
        if self.stream:
            self.active_flows.add(flow)

    def response(self, flow: http.HTTPFlow):
        # websocket flows will receive a websocket_end,
        # we don't want to persist them here already
        if self.stream and flow.websocket is None and self.new_stream():
            self.save_flow(flow)
            self.active_flows.discard(flow)

    def error(self, flow: http.HTTPFlow):
        self.response(flow)

    def done(self):
        if self.stream and self.new_stream():
            for f in self.active_flows:
                self.save_flow(f)
            self.close_stream()
            self.stream = None
