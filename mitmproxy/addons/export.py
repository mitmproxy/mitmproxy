import typing

from mitmproxy import ctx
from mitmproxy import command
from mitmproxy import flow
from mitmproxy import exceptions
from mitmproxy.utils import strutils
from mitmproxy.net.http.http1 import assemble
import mitmproxy.types

import pyperclip


def cleanup_request(f: flow.Flow):
    if not hasattr(f, "request"):
        raise exceptions.CommandError("Can't export flow with no request.")
    request = f.request.copy()  # type: ignore
    request.decode(strict=False)
    # a bit of clean-up
    if request.method == 'GET' and request.headers.get("content-length", None) == "0":
        request.headers.pop('content-length')
    request.headers.pop(':authority', None)
    return request


def cleanup_response(f: flow.Flow):
    if not hasattr(f, "response"):
        raise exceptions.CommandError("Can't export flow with no response.")
    response = f.response.copy()  # type: ignore
    response.decode(strict=False)
    return response


def curl_command(f: flow.Flow) -> str:
    data = "curl "
    request = cleanup_request(f)
    for k, v in request.headers.items(multi=True):
        data += "--compressed " if k == 'accept-encoding' else ""
        data += "-H '%s:%s' " % (k, v)
    if request.method != "GET":
        data += "-X %s " % request.method
    data += "'%s'" % request.url
    if request.content:
        data += " --data-binary '%s'" % strutils.bytes_to_escaped_str(
            request.content,
            escape_single_quotes=True
        )
    return data


def httpie_command(f: flow.Flow) -> str:
    request = cleanup_request(f)
    data = "http %s %s" % (request.method, request.url)
    for k, v in request.headers.items(multi=True):
        data += " '%s:%s'" % (k, v)
    if request.content:
        data += " <<< '%s'" % strutils.bytes_to_escaped_str(
            request.content,
            escape_single_quotes=True
        )
    return data


def raw_request(f: flow.Flow) -> bytes:
    return assemble.assemble_request(cleanup_request(f))  # type: ignore

def raw_response(f: flow.Flow) -> bytes:
    return assemble.assemble_response(cleanup_response(f))  # type: ignore


formats = dict(
    curl = curl_command,
    httpie = httpie_command,
    raw_request = raw_request,
    raw_response = raw_response,
)


class Export():
    @command.command("export.formats")
    def formats(self) -> typing.Sequence[str]:
        """
            Return a list of the supported export formats.
        """
        return list(sorted(formats.keys()))

    @command.command("export.file")
    def file(self, fmt: str, f: flow.Flow, path: mitmproxy.types.Path) -> None:
        """
            Export a flow to path.
        """
        if fmt not in formats:
            raise exceptions.CommandError("No such export format: %s" % fmt)
        func: typing.Any = formats[fmt]
        v = func(f)
        try:
            with open(path, "wb") as fp:
                if isinstance(v, bytes):
                    fp.write(v)
                else:
                    fp.write(v.encode("utf-8"))
        except IOError as e:
            ctx.log.error(str(e))

    @command.command("export.clip")
    def clip(self, fmt: str, f: flow.Flow) -> None:
        """
            Export a flow to the system clipboard.
        """
        if fmt not in formats:
            raise exceptions.CommandError("No such export format: %s" % fmt)
        func: typing.Any = formats[fmt]
        v = strutils.always_str(func(f))
        try:
            pyperclip.copy(v)
        except pyperclip.PyperclipException as e:
            ctx.log.error(str(e))
