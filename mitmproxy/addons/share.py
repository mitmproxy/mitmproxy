import os.path
import typing
import random
import datetime
import time

from mitmproxy import command
from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import io
from mitmproxy import ctx
from mitmproxy import flow

import mitmproxy.types

from mitmproxy.addons import multipart


class Share:
    def __init__(self):
        self.stream = None
        self.filt = None
        self.active_flows = set()  # type: Set[flow.Flow]

    def open_file(self, path):
        mode = "wb"
        path = os.path.expanduser(path)
        return open(path, mode)

    def read_file(self, path):
        path = os.path.expanduser(path)
        with open(path, "rb") as f:
            content = f.read()
        return content

    def start_stream_to_path(self, path, flt):
        try:
            f = self.open_file(path)
        except IOError as v:
            raise exceptions.OptionsError(str(v))
        self.stream = io.FilteredFlowWriter(f, flt)
        self.active_flows = set()

    def configure(self, updated):
        # We're already streaming - stop the previous stream and restart
        if "save_stream_filter" in updated:
            if ctx.options.save_stream_filter:
                self.filt = flowfilter.parse(ctx.options.save_stream_filter)
                if not self.filt:
                    raise exceptions.OptionsError(
                        "Invalid filter specification: %s" % ctx.options.save_stream_filter
                    )
            else:
                self.filt = None
        if "save_stream_file" in updated or "save_stream_filter" in updated:
            if self.stream:
                self.done()
            if ctx.options.save_stream_file:
                self.start_stream_to_path(ctx.options.save_stream_file, self.filt)

    def base36encode(self, integer):
        chars, encoded = "0123456789abcdefghijklmnopqrstuvwxyz", ""

        while integer > 0:
            integer, remainder = divmod(integer, 36)
            encoded = chars[remainder] + encoded

        return encoded

    @command.command("share.file")
    def share(self, flows: typing.Sequence[flow.Flow]) -> None:

        d = datetime.datetime.utcnow()
        id = self.base36encode(int(time.mktime(d.timetuple()) * 1000 * random.random()))[0:7]
        try:
            f = self.open_file(id)  # Making temporary file to store the flows
        except IOError as v:
            raise exceptions.CommandError(v) from v
        stream = io.FlowWriter(f)
        for i in flows:
            stream.add(i)
        f.close()
        content = self.read_file(id)
        res = multipart.post_multipart('http://upload.share.mitmproxy.org.s3.amazonaws.com', id, content)
        ctx.log.alert("%s" % res)
        os.remove(os.path.expanduser(id))  # Deleting the temporary file

    def tcp_start(self, flow):
        if self.stream:
            self.active_flows.add(flow)

    def tcp_end(self, flow):
        if self.stream:
            self.stream.add(flow)
            self.active_flows.discard(flow)

    def websocket_start(self, flow):
        if self.stream:
            self.active_flows.add(flow)

    def websocket_end(self, flow):
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
            for f in self.active_flows:
                self.stream.add(f)
            self.active_flows = set([])
            self.stream.fo.close()
            self.stream = None
