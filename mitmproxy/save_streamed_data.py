"""
Save streamed requests and responses

The option 'save_streamed_data' is set to a template file name. If set then streamed
requests and responses are written to individual files with a name generated from the
template. Apart from python strftime() formating the following codes can also be used:
    - %+T: The time stamp of the request
    - %+D: 'req' or 'rsp' indicating the direction of the data
    - %+C: The server connection id 
A good starting point for a template could be '~/streamed_files/%Y%m%d-%H/%+D:%+T:%+C'.
"""
from typing import Iterable, Union, Optional
from mitmproxy import flow, ctx
from datetime import datetime
from pathlib import Path
import os

class StreamSaver:
    
    def __init__(self, flow: flow.Flow, direction: str, ts):
        self.flow = flow
        self.direction = direction
        self.ts = ts
        self.fh = None
        self.path = None

    def done(self):
        if self.fh:
            self.fh.close()
            self.fh = None
        self.flow = None # Make sure we have no circular references

    def __call__(self, data: bytes) -> Union[bytes, Iterable[bytes]]:
        # End of stream?
        if len(data) == 0:
           self.done()
           return data

        if not self.fh:
            self.path = datetime.fromtimestamp(self.ts).strftime(ctx.options.save_streamed_data)
            self.path = self.path.replace('%+T', str(self.ts))
            self.path = self.path.replace('%+C', str(self.flow.server_conn.id))
            self.path = self.path.replace('%+D', self.direction)
            os.path.expanduser(self.path)

            parent = Path(self.path).parent

            try:
                if not parent.exists():
                    parent.mkdir(parents=True, exist_ok=True)
            except IOError:
                ctx.log.error(f"Failed to create directory: {parent}")

            try:
                self.fh = open(self.path, "wb", buffering=0)
            except OSError:
                ctx.log.error(f"Failed to open for writing: {self.path}")

        if self.fh:
            try:
                self.fh.write(data)
            except OSError:
                ctx.log.error(f"Failed to write to: {self.path}")

        return data

def load(loader):
    loader.add_option(
        "save_streamed_data", Optional[str], None,
        "Template for saving streamed data to files. If set each streamed request or response is written to a file with a name derived from the template. In addition to formating supported by python strftime() the code '%+T' is replaced with the time stamp of the request, '%+D' by 'req' or 'rsp' depending on the direction of the data and '%+C' by the server connection id."
    )

def requestheaders(flow):
    if ctx.options.save_streamed_data and flow.request.stream:
        flow.request.stream = StreamSaver(flow, 'req', flow.request.timestamp_start)

def responseheaders(flow):
    if isinstance(flow.request.stream, StreamSaver):
        flow.request.stream.done()
    if ctx.options.save_streamed_data and flow.response.stream:
        flow.response.stream = StreamSaver(flow, 'rsp', flow.response.timestamp_start)

def response(flow):
    if isinstance(flow.response.stream, StreamSaver):
        flow.response.stream.done()

def error(flow):
    if flow.request and isinstance(flow.request.stream, StreamSaver):
        flow.request.stream.done()
    if flow.response and isinstance(flow.response.stream, StreamSaver):
        flow.response.stream.done()
