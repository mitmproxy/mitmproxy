"""Reads HAR files into flow objects"""
import asyncio
import json
import logging
import time

from mitmproxy import command
from mitmproxy import connection
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import http
from mitmproxy import types

logger = logging.getLogger(__name__)


class ReadHar:
    def fix_headers(
        self, request_headers: list[dict[str, str]] | list[tuple[str, str]]
    ) -> http.Headers:
        """Converts provided headers into (b"header-name", b"header-value") tuples"""
        flow_headers: list[tuple[bytes, bytes]] = []
        for header in request_headers:
            # Applications that use the {"name":item,"value":item} notation are Brave,Chrome,Edge,Firefox,Charles,Fiddler,Insomnia,Safari
            if isinstance(header, dict):
                key = header["name"]
                value = header["value"]

            # Application that use the [name, value] notation is Slack
            else:
                try:
                    key = header[0]
                    value = header[1]
                except IndexError as e:
                    raise exceptions.OptionsError(str(e)) from e
            flow_headers.append((key.encode(), value.encode()))

        return http.Headers(flow_headers)

    # Don't know how to make a type annotation for the request json
    def request_to_flow(self, request_json: dict) -> http.HTTPFlow:
        """
        Creates a HTTPFlow object from a given entry in HAR file
        """

        request_method = request_json["request"]["method"]
        request_url = request_json["request"]["url"]
        server_address = request_json.get("serverIPAddress", None)
        request_headers = self.fix_headers(request_json["request"]["headers"])
        # List contains all the representations of an http request across different HAR files
        if request_url.startswith("http://"):
            port = 80
        else:
            port = 443

        client_conn = connection.Client(
            peername=("127.0.0.1", 0),
            sockname=("127.0.0.1", 0),
            # TODO Get time info from HAR File
            timestamp_start=time.time(),
        )
        # TODO find server address if "serverIPAddress" == ""
        if server_address:
            server_conn = connection.Server(address=(server_address, port))
        else:
            server_conn = connection.Server(address=None)

        new_flow = http.HTTPFlow(client_conn, server_conn)
        new_flow.request = http.Request.make(
            request_method, request_url, "", request_headers
        )

        response_code = request_json["response"]["status"]

        # In Firefox HAR files images don't include response bodies
        response_content = request_json["response"]["content"].get("text", "")

        response_headers = self.fix_headers(request_json["response"]["headers"])

        new_flow.response = http.Response.make(
            response_code, response_content, response_headers
        )

        return new_flow

    @command.command("readhar")
    def read_har(
        self,
        path: types.Path,
    ) -> None:
        """
        Reads a HAR file into mitmproxy. Loads a flow for each entry in given HAR file.
        """
        flows = []
        with open(path) as fp:
            try:
                har_file = json.load(fp)
            except Exception:
                raise exceptions.CommandError(
                    "Unable to read HAR file. Please provide a valid HAR file"
                )

        for request_json in har_file["log"]["entries"]:
            flow = self.request_to_flow(request_json)
            flows.append(flow)

        async def load_flows() -> None:
            for flow in flows:
                await ctx.master.load_flow(flow)

        asyncio.create_task(load_flows())


addons = [ReadHar()]
