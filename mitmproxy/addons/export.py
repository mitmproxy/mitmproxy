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


def cleanup_request(f: flow.Flow) -> http.HTTPRequest:
    if not getattr(f, "request", None):
        raise exceptions.CommandError("Can't export flow with no request.")
    assert isinstance(f, http.HTTPFlow)
    request = f.request.copy()
    request.decode(strict=False)
    # a bit of clean-up - these headers should be automatically set by curl/httpie
    request.headers.pop('content-length')
    if request.headers.get("host", "") == request.host:
        request.headers.pop("host")
    if request.headers.get(":authority", "") == request.host:
        request.headers.pop(":authority")
    return request


def cleanup_response(f: flow.Flow) -> http.HTTPResponse:
    if not getattr(f, "response", None):
        raise exceptions.CommandError("Can't export flow with no response.")
    assert isinstance(f, http.HTTPFlow)
    response = f.response.copy()  # type: ignore
    response.decode(strict=False)
    return response


def request_content_for_console(request: http.HTTPRequest) -> str:
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
    args = ["curl"]
    for k, v in request.headers.items(multi=True):
        if k.lower() == "accept-encoding":
            args.append("--compressed")
        else:
            args += ["-H", f"{k}: {v}"]

    if request.method != "GET":
        args += ["-X", request.method]
    args.append(request.url)
    if request.content:
        args += ["-d", request_content_for_console(request)]
    return ' '.join(shlex.quote(arg) for arg in args)


def httpie_command(f: flow.Flow) -> str:
    request = cleanup_request(f)
    args = ["http", request.method, request.url]
    for k, v in request.headers.items(multi=True):
        args.append(f"{k}: {v}")
    cmd = ' '.join(shlex.quote(arg) for arg in args)
    if request.content:
        cmd += " <<< " + shlex.quote(request_content_for_console(request))
    return cmd


def raw_request(f: flow.Flow) -> bytes:
    return assemble.assemble_request(cleanup_request(f))


def raw_response(f: flow.Flow) -> bytes:
    return assemble.assemble_response(cleanup_response(f))


def raw(f: flow.Flow, separator=b"\r\n\r\n") -> bytes:
    """Return either the request or response if only one exists, otherwise return both"""
    request_present = hasattr(f, "request") and f.request  # type: ignore
    response_present = hasattr(f, "response") and f.response  # type: ignore

    if not (request_present or response_present):
        raise exceptions.CommandError("Can't export flow with no request or response.")

    if request_present and response_present:
        return b"".join([raw_request(f), separator, raw_response(f)])
    elif not request_present:
        return raw_response(f)
    else:
        return raw_request(f)


formats = dict(
    curl=curl_command,
    httpie=httpie_command,
    raw=raw,
    raw_request=raw_request,
    raw_response=raw_response,
)


class Export():
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
        except IOError as e:
            ctx.log.error(str(e))

    @command.command("export.clip")
    def clip(self, format: str, flow: flow.Flow) -> None:
        """
            Export a flow to the system clipboard.
        """
        if format not in formats:
            raise exceptions.CommandError("No such export format: %s" % format)
        func: typing.Any = formats[format]
        v = strutils.always_str(func(flow))
        try:
            pyperclip.copy(v)
        except pyperclip.PyperclipException as e:
            ctx.log.error(str(e))
