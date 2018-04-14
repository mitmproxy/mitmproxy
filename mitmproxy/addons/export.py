import typing

from mitmproxy import ctx
from mitmproxy import command
from mitmproxy import flow
from mitmproxy import exceptions
from mitmproxy.utils import strutils
from mitmproxy.net.http.http1 import assemble
import mitmproxy.types

import pyperclip


def raise_if_missing_request(f: flow.Flow) -> None:
    if not hasattr(f, "request"):
        raise exceptions.CommandError("Can't export flow with no request.")


def curl_command(f: flow.Flow) -> str:
    raise_if_missing_request(f)
    data = "curl "
    request = f.request.copy()  # type: ignore
    request.decode(strict=False)
    for k, v in request.headers.items(multi=True):
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
    raise_if_missing_request(f)
    request = f.request.copy()  # type: ignore
    data = "http %s " % request.method
    request.decode(strict=False)
    data += "%s" % request.url
    for k, v in request.headers.items(multi=True):
        data += " '%s:%s'" % (k, v)
    if request.content:
        data += " <<< '%s'" % strutils.bytes_to_escaped_str(
            request.content,
            escape_single_quotes=True
        )
    return data


def raw(f: flow.Flow) -> bytes:
    raise_if_missing_request(f)
    return assemble.assemble_request(f.request)  # type: ignore


formats = dict(
    curl = curl_command,
    httpie = httpie_command,
    raw = raw,
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
