import io
import csv
import typing
from mitmproxy import command
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import ctx
from mitmproxy import certs
from mitmproxy.utils import strutils

import pyperclip


def headername(spec: str):
    if not (spec.startswith("header[") and spec.endswith("]")):
        raise exceptions.CommandError("Invalid header spec: %s" % spec)
    return spec[len("header["):-1].strip()


flow_shortcuts = {
    "q": "request",
    "s": "response",
    "cc": "client_conn",
    "sc": "server_conn",
}


def is_addr(v):
    return isinstance(v, tuple) and len(v) > 1


def extract(cut: str, f: flow.Flow) -> typing.Union[str, bytes]:
    path = cut.split(".")
    current = f  # type: typing.Any
    for i, spec in enumerate(path):
        if spec.startswith("_"):
            raise exceptions.CommandError("Can't access internal attribute %s" % spec)
        if isinstance(current, flow.Flow):
            spec = flow_shortcuts.get(spec, spec)

        part = getattr(current, spec, None)
        if i == len(path) - 1:
            if spec == "port" and is_addr(current):
                return str(current[1])
            if spec == "host" and is_addr(current):
                return str(current[0])
            elif spec.startswith("header["):
                return current.headers.get(headername(spec), "")
            elif isinstance(part, bytes):
                return part
            elif isinstance(part, bool):
                return "true" if part else "false"
            elif isinstance(part, certs.SSLCert):
                return part.to_pem().decode("ascii")
        current = part
    return str(current or "")


class Cut:
    @command.command("cut")
    def cut(
        self,
        flows: typing.Sequence[flow.Flow],
        cuts: typing.Sequence[command.Cut]
    ) -> command.Cuts:
        """
            Cut data from a set of flows. Cut specifications are attribute paths
            from the base of the flow object, with a few conveniences - "q",
            "s", "cc" and "sc" are shortcuts for request, response, client_conn
            and server_conn, "port" and "host" retrieve parts of an address
            tuple, ".header[key]" retrieves a header value. Return values
            converted to strings or bytes: SSL certicates are converted to PEM
            format, bools are "true" or "false", "bytes" are preserved, and all
            other values are converted to strings.
        """
        ret = []
        for f in flows:
            ret.append([extract(c, f) for c in cuts])
        return ret

    @command.command("cut.save")
    def save(
        self,
        flows: typing.Sequence[flow.Flow],
        cuts: typing.Sequence[command.Cut],
        path: command.Path
    ) -> None:
        """
            Save cuts to file. If there are multiple flows or cuts, the format
            is UTF-8 encoded CSV. If there is exactly one row and one column,
            the data is written to file as-is, with raw bytes preserved. If the
            path is prefixed with a "+", values are appended if there is an
            existing file.
        """
        append = False
        if path.startswith("+"):
            append = True
            path = command.Path(path[1:])
        if len(cuts) == 1 and len(flows) == 1:
            with open(path, "ab" if append else "wb") as fp:
                if fp.tell() > 0:
                    # We're appending to a file that already exists and has content
                    fp.write(b"\n")
                for v in [extract(cuts[0], f) for f in flows]:
                    if isinstance(v, bytes):
                        fp.write(v)
                    else:
                        fp.write(v.encode("utf8"))
            ctx.log.alert("Saved single cut.")
        else:
            with open(path, "a" if append else "w", newline='', encoding="utf8") as fp:
                writer = csv.writer(fp)
                for f in flows:
                    vals = [extract(c, f) for c in cuts]
                    writer.writerow(
                        [strutils.always_str(x) or "" for x in vals]  # type: ignore
                    )
            ctx.log.alert("Saved %s cuts over %d flows as CSV." % (len(cuts), len(flows)))

    @command.command("cut.clip")
    def clip(
        self,
        flows: typing.Sequence[flow.Flow],
        cuts: typing.Sequence[command.Cut],
    ) -> None:
        """
            Send cuts to the clipboard. If there are multiple flows or cuts, the
            format is UTF-8 encoded CSV. If there is exactly one row and one
            column, the data is written to file as-is, with raw bytes preserved.
        """
        fp = io.StringIO(newline="")
        if len(cuts) == 1 and len(cuts[0]) == 1:
            v = cuts[0][0]
            if isinstance(v, bytes):
                fp.write(strutils.always_str(v))
            else:
                fp.write("utf8")
            ctx.log.alert("Clipped single cut.")
        else:
            writer = csv.writer(fp)
            for r in cuts:
                writer.writerow(
                    [strutils.always_str(c) or "" for c in r]  # type: ignore
                )
            ctx.log.alert("Clipped %s cuts as CSV." % len(cuts))
        pyperclip.copy(fp.getvalue())
