import typing

from mitmproxy import command
from mitmproxy import flow
from mitmproxy import exceptions
from mitmproxy.utils import strutils
from mitmproxy.net.http.http1 import assemble

import pyperclip


def curl_command(f: flow.Flow) -> str:
    if not hasattr(f, "request"):
        raise exceptions.CommandError("Can't export flow with no request.")
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


def raw(f: flow.Flow) -> bytes:
    if not hasattr(f, "request"):
        raise exceptions.CommandError("Can't export flow with no request.")
    return assemble.assemble_request(f.request)  # type: ignore


formats = dict(
    curl = curl_command,
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
    def file(self, fmt: str, f: flow.Flow, path: str) -> None:
        """
            Export a flow to path.
        """
        if fmt not in formats:
            raise exceptions.CommandError("No such export format: %s" % fmt)
        func = formats[fmt]  # type: typing.Any
        v = func(f)
        with open(path, "wb") as fp:
            if isinstance(v, bytes):
                fp.write(v)
            else:
                fp.write(v.encode("utf-8"))

    @command.command("export.clip")
    def clip(self, fmt: str, f: flow.Flow) -> None:
        """
            Export a flow to the system clipboard.
        """
        if fmt not in formats:
            raise exceptions.CommandError("No such export format: %s" % fmt)
        func = formats[fmt]  # type: typing.Any
        v = strutils.always_str(func(f))
        pyperclip.copy(v)
