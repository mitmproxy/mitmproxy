#!/usr/bin/env python
# dump content to files based on a filter
# usage: mitmdump -s httpdump.py "~ts application/json"
#
# options:
#   - dumper_folder: content dump destination folder (default: ./httpdump)
#   - open_browser: open integrated browser with proxy configured at start (default: true)
#
# remember to add your own mitmproxy authorative certs in your browser/os!
# certs docs: https://docs.mitmproxy.org/stable/concepts-certificates/
# filter expressions docs: https://docs.mitmproxy.org/stable/concepts-filters/
import logging
import mimetypes
import os
from pathlib import Path

from mitmproxy import ctx, http
from mitmproxy import flowfilter


class HTTPDump:
    def load(self, loader):
        self.filter = ctx.options.dumper_filter

        loader.add_option(
            name="dumper_folder",
            typespec=str,
            default="httpdump",
            help="content dump destination folder",
        )
        loader.add_option(
            name="open_browser",
            typespec=bool,
            default=True,
            help="open integrated browser at start"
        )

    def running(self):
        if ctx.options.open_browser:
            ctx.master.commands.call("browser.start")

    def configure(self, updated):
        if "dumper_filter" in updated:
            self.filter = ctx.options.dumper_filter

    def response(self, flow: http.HTTPFlow) -> None:
        if flowfilter.match(self.filter, flow):
            self.dump(flow)

    def dump(self, flow: http.HTTPFlow):
        if not flow.response:
            return

        # create dir
        folder = Path(ctx.options.dumper_folder) / flow.request.host
        if not folder.exists():
            os.makedirs(folder)

        # calculate path
        path = "-".join(flow.request.path_components)
        filename = "-".join([path, flow.id])
        content_type = flow.response.headers.get("content-type", "").split(";")[0]
        ext = mimetypes.guess_extension(content_type) or ""
        filepath = folder / f"{filename}{ext}"

        # dump to file
        if flow.response.content:
            with open(filepath, "wb") as f:
                f.write(flow.response.content)
            logging.info(f"Saved! {filepath}")


addons = [HTTPDump()]
