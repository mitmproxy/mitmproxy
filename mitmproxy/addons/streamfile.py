import os.path

from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import io
from mitmproxy import ctx


class StreamFile:
    def __init__(self):
        self.stream = None
        self.filt = None
        self.active_flows = set()  # type: Set[flow.Flow]

    def start_stream_to_path(self, path, mode, flt):
        path = os.path.expanduser(path)
        try:
            f = open(path, mode)
        except IOError as v:
            raise exceptions.OptionsError(str(v))
        self.stream = io.FilteredFlowWriter(f, flt)
        self.active_flows = set()

    def configure(self, updated):
        # We're already streaming - stop the previous stream and restart
        if "streamfile_filter" in updated:
            if ctx.options.streamfile_filter:
                self.filt = flowfilter.parse(ctx.options.streamfile_filter)
                if not self.filt:
                    raise exceptions.OptionsError(
                        "Invalid filter specification: %s" % ctx.options.streamfile_filter
                    )
            else:
                self.filt = None
        if "streamfile" in updated:
            if self.stream:
                self.done()
            if ctx.options.streamfile:
                if ctx.options.streamfile.startswith("+"):
                    path = ctx.options.streamfile[1:]
                    mode = "ab"
                else:
                    path = ctx.options.streamfile
                    mode = "wb"
                self.start_stream_to_path(path, mode, self.filt)

    def tcp_start(self, flow):
        if self.stream:
            self.active_flows.add(flow)

    def tcp_end(self, flow):
        if self.stream:
            self.stream.add(flow)
            self.active_flows.discard(flow)

    def response(self, flow):
        if self.stream:
            self.stream.add(flow)
            self.active_flows.discard(flow)

    def request(self, flow):
        if self.stream:
            self.active_flows.add(flow)

    def done(self):
        if self.stream:
            for flow in self.active_flows:
                self.stream.add(flow)
            self.active_flows = set([])
            self.stream.fo.close()
            self.stream = None
