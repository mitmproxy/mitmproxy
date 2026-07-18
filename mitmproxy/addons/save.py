import logging
import os.path
import sys
from collections.abc import Sequence
from datetime import datetime
from functools import lru_cache
from io import BufferedWriter
from pathlib import Path
from typing import Literal
from typing import Optional

import zstandard as zstd

import mitmproxy.types
from mitmproxy import command
from mitmproxy import ctx
from mitmproxy import dns
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import flowfilter
from mitmproxy import http
from mitmproxy import io
from mitmproxy import tcp
from mitmproxy import udp
from mitmproxy.log import ALERT


@lru_cache
def _path(path: str) -> str:
    """Extract the path from a path spec (which may have an extra "+" at the front)"""
    if path.startswith("+"):
        path = path[1:]
    return os.path.expanduser(path)


@lru_cache
def _mode(path: str) -> Literal["ab", "wb"]:
    """Extract the writing mode (overwrite or append) from a path spec"""
    if path.startswith("+"):
        return "ab"
    else:
        return "wb"


class Save:
    def __init__(self) -> None:
        self.stream: io.FilteredFlowWriter | None = None
        self.filt: flowfilter.TFilter | None = None
        self.active_flows: set[flow.Flow] = set()
        self.current_path: str | None = None
        self._compressed: bool = False
        self._raw_file: BufferedWriter | None = None
        self._compressor_writer: zstd.ZstdCompressionWriter | None = None

    def load(self, loader):
        loader.add_option(
            "save_stream_file",
            Optional[str],
            None,
            """
            Stream flows to file as they arrive. Prefix path with + to append.
            The full path can use python strftime() formating, missing
            directories are created as needed. A new file is opened every time
            the formatted string changes. Use save_stream_compression to
            compress output with zstandard.
            """,
        )
        loader.add_option(
            "save_stream_filter",
            Optional[str],
            None,
            "Filter which flows are written to file.",
        )
        loader.add_option(
            "save_stream_compression",
            bool,
            False,
            "Compress stream files on the fly using zstandard.",
        )

    def configure(self, updated):
        if "save_stream_filter" in updated:
            if ctx.options.save_stream_filter:
                try:
                    self.filt = flowfilter.parse(ctx.options.save_stream_filter)
                except ValueError as e:
                    raise exceptions.OptionsError(str(e)) from e
            else:
                self.filt = None
        if (
            "save_stream_file" in updated
            or "save_stream_filter" in updated
            or "save_stream_compression" in updated
        ):
            if ctx.options.save_stream_file:
                try:
                    self.maybe_rotate_to_new_file()
                except OSError as e:
                    raise exceptions.OptionsError(str(e)) from e
                assert self.stream
                self.stream.flt = self.filt
            else:
                self.done()

    def maybe_rotate_to_new_file(self) -> None:
        path = datetime.today().strftime(_path(ctx.options.save_stream_file))
        compressed = ctx.options.save_stream_compression
        if self.current_path == path and self._compressed == compressed:
            return

        self._close_stream()

        new_log_file = Path(path)
        new_log_file.parent.mkdir(parents=True, exist_ok=True)

        mode = _mode(ctx.options.save_stream_file)
        if ctx.options.save_stream_compression:
            self._raw_file = new_log_file.open(mode)
            cctx = zstd.ZstdCompressor()
            self._compressor_writer = cctx.stream_writer(self._raw_file, closefd=False)
            self.stream = io.FilteredFlowWriter(self._compressor_writer, self.filt)
        else:
            self._raw_file = None
            self._compressor_writer = None
            self.stream = io.FilteredFlowWriter(new_log_file.open(mode), self.filt)
        self.current_path = path
        self._compressed = compressed

    def _close_stream(self) -> None:
        if self.stream:
            if self._compressor_writer:
                self._compressor_writer.close()
            if self._raw_file:
                self._raw_file.close()
            else:
                self.stream.fo.close()
            self.stream = None
            self._compressor_writer = None
            self._raw_file = None

    def save_flow(self, flow: flow.Flow) -> None:
        """
        Write the flow to the stream, but first check if we need to rotate to a new file.
        """
        if not self.stream:
            return
        try:
            self.maybe_rotate_to_new_file()
            self.stream.add(flow)
        except OSError as e:
            # If we somehow fail to write flows to a logfile, we really want to crash visibly
            # instead of letting traffic through unrecorded.
            # No normal logging here, that would not be triggered anymore.
            sys.stderr.write(f"Error while writing to {self.current_path}: {e}")
            sys.exit(1)
        else:
            self.active_flows.discard(flow)

    def done(self) -> None:
        if self.stream:
            for f in self.active_flows:
                self.stream.add(f)
            self.active_flows.clear()

            self.current_path = None
            self._close_stream()

    @command.command("save.file")
    def save(self, flows: Sequence[flow.Flow], path: mitmproxy.types.Path) -> None:
        """
        Save flows to a file. If the path starts with a +, flows are
        appended to the file, otherwise it is over-written.
        """
        try:
            with open(_path(path), _mode(path)) as f:
                stream = io.FlowWriter(f)
                for i in flows:
                    stream.add(i)
        except OSError as e:
            raise exceptions.CommandError(e) from e
        if path.endswith(".har") or path.endswith(".zhar"):  # pragma: no cover
            logging.log(
                ALERT,
                f"Saved as mitmproxy dump file. To save HAR files, use the `save.har` command.",
            )
        else:
            logging.log(ALERT, f"Saved {len(flows)} flows.")

    def tcp_start(self, flow: tcp.TCPFlow):
        if self.stream:
            self.active_flows.add(flow)

    def tcp_end(self, flow: tcp.TCPFlow):
        self.save_flow(flow)

    def tcp_error(self, flow: tcp.TCPFlow):
        self.tcp_end(flow)

    def udp_start(self, flow: udp.UDPFlow):
        if self.stream:
            self.active_flows.add(flow)

    def udp_end(self, flow: udp.UDPFlow):
        self.save_flow(flow)

    def udp_error(self, flow: udp.UDPFlow):
        self.udp_end(flow)

    def websocket_end(self, flow: http.HTTPFlow):
        self.save_flow(flow)

    def request(self, flow: http.HTTPFlow):
        if self.stream:
            self.active_flows.add(flow)

    def response(self, flow: http.HTTPFlow):
        # websocket flows will receive a websocket_end,
        # we don't want to persist them here already
        if flow.websocket is None:
            self.save_flow(flow)

    def error(self, flow: http.HTTPFlow):
        self.response(flow)

    def dns_request(self, flow: dns.DNSFlow):
        if self.stream:
            self.active_flows.add(flow)

    def dns_response(self, flow: dns.DNSFlow):
        self.save_flow(flow)

    def dns_error(self, flow: dns.DNSFlow):
        self.save_flow(flow)
