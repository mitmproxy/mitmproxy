"""
Save streamed requests and responses

If the option 'save_streamed_data' is set to a format string then
streamed requests and responses are written to individual files with a name
derived from the string. Apart from python strftime() formating (using the
request start time) the following codes can also be used:
    - %+T: The time stamp of the request with microseconds
    - %+D: 'req' or 'rsp' indicating the direction of the data
    - %+I: The client connection ID
    - %+C: The client IP address
A good starting point for a template could be '~/streamed_files/%+D:%+T:%+I',
a more complex example is '~/streamed_files/%+C/%Y-%m-%d%/%+D:%+T:%+I'.
The client connection ID combined with the request time stamp should be unique
for associating a file with its corresponding flow in the stream saved with
'--save-stream-file'.

This addon is not compatible with addons that use the same mechanism to
capture streamed data, http-stream-modify.py for instance.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from mitmproxy import ctx


class StreamSaver:
    TAG = "save_streamed_data: "

    def __init__(self, flow, direction):
        self.flow = flow
        self.direction = direction
        self.fh = None
        self.path = None

    def done(self):
        if self.fh:
            self.fh.close()
            self.fh = None
        # Make sure we have no circular references
        self.flow = None

    def __call__(self, data):
        # End of stream?
        if len(data) == 0:
            self.done()
            return data

        # Just in case the option changes while a stream is in flight
        if not ctx.options.save_streamed_data:
            return data

        # This is a safeguard but should not be needed
        if not self.flow or not self.flow.request:
            return data

        if not self.fh:
            self.path = datetime.fromtimestamp(
                self.flow.request.timestamp_start
            ).strftime(ctx.options.save_streamed_data)
            self.path = self.path.replace("%+T", str(self.flow.request.timestamp_start))
            self.path = self.path.replace("%+I", str(self.flow.client_conn.id))
            self.path = self.path.replace("%+D", self.direction)
            self.path = self.path.replace("%+C", self.flow.client_conn.address[0])
            self.path = os.path.expanduser(self.path)

            parent = Path(self.path).parent
            try:
                if not parent.exists():
                    parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                logging.error(f"{self.TAG}Failed to create directory: {parent}")

            try:
                self.fh = open(self.path, "wb", buffering=0)
            except OSError:
                logging.error(f"{self.TAG}Failed to open for writing: {self.path}")

        if self.fh:
            try:
                self.fh.write(data)
            except OSError:
                logging.error(f"{self.TAG}Failed to write to: {self.path}")

        return data


def load(loader):
    loader.add_option(
        "save_streamed_data",
        Optional[str],
        None,
        "Format string for saving streamed data to files. If set each streamed request or response is written "
        "to a file with a name derived from the string. In addition to formating supported by python "
        "strftime() (using the request start time) the code '%+T' is replaced with the time stamp of the request, "
        "'%+D' by 'req' or 'rsp' depending on the direction of the data, '%+C' by the client IP addresses and "
        "'%+I' by the client connection ID.",
    )


def requestheaders(flow):
    if ctx.options.save_streamed_data and flow.request.stream:
        flow.request.stream = StreamSaver(flow, "req")


def responseheaders(flow):
    if isinstance(flow.request.stream, StreamSaver):
        flow.request.stream.done()
    if ctx.options.save_streamed_data and flow.response.stream:
        flow.response.stream = StreamSaver(flow, "rsp")


def response(flow):
    if isinstance(flow.response.stream, StreamSaver):
        flow.response.stream.done()


def error(flow):
    if flow.request and isinstance(flow.request.stream, StreamSaver):
        flow.request.stream.done()
    if flow.response and isinstance(flow.response.stream, StreamSaver):
        flow.response.stream.done()
