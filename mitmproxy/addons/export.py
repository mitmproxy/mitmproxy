import shlex
import typing

import pyperclip

import mitmproxy.types
from mitmproxy import command
from mitmproxy import ctx, http
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy.net.http.http1 import assemble
from mitmproxy.utils import strutils


def cleanup_request(f: flow.Flow) -> http.Request:
    if not getattr(f, "request", None):
        raise exceptions.CommandError("Can't export flow with no request.")
    assert isinstance(f, http.HTTPFlow)
    request = f.request.copy()
    request.decode(strict=False)
    return request


def pop_headers(request: http.Request) -> http.Request:
    # Remove some headers that are redundant for curl/httpie export
    request.headers.pop('content-length')
    if request.headers.get("host", "") == request.host:
        request.headers.pop("host")
    if request.headers.get(":authority", "") == request.host:
        request.headers.pop(":authority")
    return request


def cleanup_response(f: flow.Flow) -> http.Response:
    if not getattr(f, "response", None):
        raise exceptions.CommandError("Can't export flow with no response.")
    assert isinstance(f, http.HTTPFlow)
    response = f.response.copy()  # type: ignore
    response.decode(strict=False)
    return response


def request_content_for_console(request: http.Request) -> str:
    try:
        text = request.get_text(strict=True)
        assert text
    except ValueError:
        # shlex.quote doesn't support a bytes object
        # see https://github.com/python/cpython/pull/10871
        raise exceptions.CommandError("Request content must be valid unicode")
    escape_control_chars = {chr(i): f"\\x{i:02x}" for i in range(32)}
    return "".join(
        escape_control_chars.get(x, x)
        for x in text
    )


def curl_command(f: flow.Flow) -> str:
    request = cleanup_request(f)
    request = pop_headers(request)
    args = ["curl"]

    server_addr = f.server_conn.peername[0] if f.server_conn.peername else None

    if ctx.options.export_preserve_original_ip and server_addr and request.pretty_host != server_addr:
        resolve = "{}:{}:[{}]".format(request.pretty_host, request.port, server_addr)
        args.append("--resolve")
        args.append(resolve)

    for k, v in request.headers.items(multi=True):
        if k.lower() == "accept-encoding":
            args.append("--compressed")
        else:
            args += ["-H", f"{k}: {v}"]

    if request.method != "GET":
        args += ["-X", request.method]

    args.append(request.pretty_url)

    if request.content:
        args += ["-d", request_content_for_console(request)]
    return ' '.join(shlex.quote(arg) for arg in args)


def httpie_command(f: flow.Flow) -> str:
    request = cleanup_request(f)
    request = pop_headers(request)

    # TODO: Once https://github.com/httpie/httpie/issues/414 is implemented, we
    # should ensure we always connect to the IP address specified in the flow,
    # similar to how it's done in curl_command.
    url = request.pretty_url

    args = ["http", request.method, url]
    for k, v in request.headers.items(multi=True):
        args.append(f"{k}: {v}")
    cmd = ' '.join(shlex.quote(arg) for arg in args)
    if request.content:
        cmd += " <<< " + shlex.quote(request_content_for_console(request))
    return cmd


def raw_request(f: flow.Flow) -> bytes:
    request = cleanup_request(f)
    if request.raw_content is None:
        raise exceptions.CommandError("Request content missing.")
    return assemble.assemble_request(request)


def raw_response(f: flow.Flow) -> bytes:
    response = cleanup_response(f)
    if response.raw_content is None:
        raise exceptions.CommandError("Response content missing.")
    return assemble.assemble_response(response)


def raw(f: flow.Flow, separator=b"\r\n\r\n") -> bytes:
    """Return either the request or response if only one exists, otherwise return both"""
    request_present = isinstance(f, http.HTTPFlow) and f.request and f.request.raw_content is not None
    response_present = isinstance(f, http.HTTPFlow) and f.response and f.response.raw_content is not None

    if request_present and response_present:
        return b"".join([raw_request(f), separator, raw_response(f)])
    elif request_present:
        return raw_request(f)
    elif response_present:
        return raw_response(f)
    else:
        raise exceptions.CommandError("Can't export flow with no request or response.")


formats: typing.Dict[str, typing.Callable[[flow.Flow], typing.Union[str, bytes]]] = dict(
    curl=curl_command,
    httpie=httpie_command,
    raw=raw,
    raw_request=raw_request,
    raw_response=raw_response,
)


class Export:
    def load(self, loader):
        loader.add_option(
            "export_preserve_original_ip", bool, False,
            """
            When exporting a request as an external command, make an effort to
            connect to the same IP as in the original request. This helps with
            reproducibility in cases where the behaviour depends on the
            particular host we are connecting to. Currently this only affects
            curl exports.
            """
        )

    @command.command("export.formats")
    def formats(self) -> typing.Sequence[str]:
        """
            Return a list of the supported export formats.
        """
        return list(sorted(formats.keys()))

    @command.command("export.file")
    def file(self, format: str, flow: flow.Flow, path: mitmproxy.types.Path) -> None:
        """
            Export a flow to path.
        """
        if format not in formats:
            raise exceptions.CommandError("No such export format: %s" % format)
        func: typing.Any = formats[format]
        v = func(flow)
        try:
            with open(path, "wb") as fp:
                if isinstance(v, bytes):
                    fp.write(v)
                else:
                    fp.write(v.encode("utf-8"))
        except OSError as e:
            ctx.log.error(str(e))

    @command.command("export.clip")
    def clip(self, format: str, f: flow.Flow) -> None:
        """
            Export a flow to the system clipboard.
        """
        if format not in formats:
            raise exceptions.CommandError("No such export format: %s" % format)
        func = formats[format]

        val = strutils.always_str(func(f), "utf8", "backslashreplace")
        try:
            pyperclip.copy(val)
        except pyperclip.PyperclipException as e:
            ctx.log.error(str(e))
