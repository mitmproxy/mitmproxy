from __future__ import absolute_import, print_function, division
import os.path

from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy.flow import io


class Stream:
    def __init__(self):
        self.stream = None

    def start_stream_to_path(self, path, mode, filt):
        path = os.path.expanduser(path)
        try:
            f = open(path, mode)
        except IOError as v:
            return str(v)
        self.stream = io.FilteredFlowWriter(f, filt)

    def configure(self, options):
        # We're already streaming - stop the previous stream and restart
        if self.stream:
            self.done()

        if options.outfile:
            filt = None
            if options.get("filtstr"):
                filt = filt.parse(options.filtstr)
                if not filt:
                    raise exceptions.OptionsError(
                        "Invalid filter specification: %s" % options.filtstr
                    )
            path, mode = options.outfile
            if mode not in ("wb", "ab"):
                raise exceptions.OptionsError("Invalid mode.")
            err = self.start_stream_to_path(path, mode, filt)
            if err:
                raise exceptions.OptionsError(err)

    def done(self):
        if self.stream:
            for flow in ctx.master.active_flows:
                self.stream.add(flow)
            self.stream.fo.close()
            self.stream = None

    def tcp_close(self):
        if self.stream:
            self.stream.add(ctx.flow)

    def response(self):
        if self.stream:
            self.stream.add(ctx.flow)
