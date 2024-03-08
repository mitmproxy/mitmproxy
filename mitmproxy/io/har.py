"""Reads HAR files into flow objects"""

import base64
import logging
import time
from datetime import datetime

from mitmproxy import connection
from mitmproxy import exceptions
from mitmproxy import http
from mitmproxy.net.http.headers import infer_content_encoding

logger = logging.getLogger(__name__)


def fix_headers(
    request_headers: list[dict[str, str]] | list[tuple[str, str]],
) -> http.Headers:
    """Converts provided headers into (b"header-name", b"header-value") tuples"""
    flow_headers: list[tuple[bytes, bytes]] = []
    for header in request_headers:
        # Applications that use the {"name":item,"value":item} notation are Brave,Chrome,Edge,Firefox,Charles,Fiddler,Insomnia,Safari
        if isinstance(header, dict):
            key = header["name"]
            value = header["value"]

        # Application that uses the [name, value] notation is Slack

        else:
            try:
                key = header[0]
                value = header[1]
            except IndexError as e:
                raise exceptions.OptionsError(str(e)) from e
        flow_headers.append((key.encode(), value.encode()))

    return http.Headers(flow_headers)


def request_to_flow(request_json: dict) -> http.HTTPFlow:
    """
    Creates a HTTPFlow object from a given entry in HAR file
    """

    timestamp_start = datetime.fromisoformat(
        request_json["startedDateTime"].replace("Z", "+00:00")
    ).timestamp()
    timestamp_end = timestamp_start + request_json["time"]
    request_method = request_json["request"]["method"]
    request_url = request_json["request"]["url"]
    server_address = request_json.get("serverIPAddress", None)
    request_headers = fix_headers(request_json["request"]["headers"])

    http_version_req = request_json["request"]["httpVersion"]
    http_version_resp = request_json["response"]["httpVersion"]

    request_content = ""
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

    if server_address:
        server_conn = connection.Server(address=(server_address, port))
    else:
        server_conn = connection.Server(address=None)

    new_flow = http.HTTPFlow(client_conn, server_conn)

    if "postData" in request_json["request"]:
        request_content = request_json["request"]["postData"]["text"]

    new_flow.request = http.Request.make(
        request_method, request_url, request_content, request_headers
    )

    response_code = request_json["response"]["status"]

    # In Firefox HAR files images don't include response bodies
    response_content = request_json["response"]["content"].get("text", "")
    content_encoding = request_json["response"]["content"].get("encoding", None)
    response_headers = fix_headers(request_json["response"]["headers"])

    if content_encoding == "base64":
        response_content = base64.b64decode(response_content)
    elif isinstance(response_content, str):
        # Convert text to bytes, as in `Response.set_text`
        try:
            response_content = http.encoding.encode(
                response_content,
                (
                    content_encoding
                    or infer_content_encoding(response_headers.get("content-type", ""))
                ),
            )
        except ValueError:
            # Fallback to UTF-8
            response_content = response_content.encode(
                "utf-8", errors="surrogateescape"
            )

    # Then encode the content, as in `Response.set_content`
    response_content = http.encoding.encode(
        response_content, response_headers.get("content-encoding") or "identity"
    )

    new_flow.response = http.Response(
        b"HTTP/1.1",
        response_code,
        http.status_codes.RESPONSES.get(response_code, "").encode(),
        response_headers,
        response_content,
        None,
        timestamp_start,
        timestamp_end,
    )

    # Update timestamps

    new_flow.request.timestamp_start = timestamp_start
    new_flow.request.timestamp_end = timestamp_end

    new_flow.client_conn.timestamp_start = timestamp_start
    new_flow.client_conn.timestamp_end = timestamp_end

    # Update HTTP version

    match http_version_req:
        case "http/2.0":
            new_flow.request.http_version = "HTTP/2"
        case "HTTP/2":
            new_flow.request.http_version = "HTTP/2"
        case "HTTP/3":
            new_flow.request.http_version = "HTTP/3"
        case _:
            new_flow.request.http_version = "HTTP/1.1"
    match http_version_resp:
        case "http/2.0":
            new_flow.response.http_version = "HTTP/2"
        case "HTTP/2":
            new_flow.response.http_version = "HTTP/2"
        case "HTTP/3":
            new_flow.response.http_version = "HTTP/3"
        case _:
            new_flow.response.http_version = "HTTP/1.1"

    return new_flow
