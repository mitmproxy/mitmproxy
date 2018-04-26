import io
import csv
import typing
import os.path

from mitmproxy import command
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import ctx
from mitmproxy import certs
from mitmproxy.utils import strutils
import mitmproxy.types

import pyperclip


def headername(spec: str):
    if not (spec.startswith("header[") and spec.endswith("]")):
        raise exceptions.CommandError("Invalid header spec: %s" % spec)
    return spec[len("header["):-1].strip()


def is_addr(v):
    return isinstance(v, tuple) and len(v) > 1


def extract(cut: str, f: flow.Flow) -> typing.Union[str, bytes]:
    path = cut.split(".")
    current: typing.Any = f
    for i, spec in enumerate(path):
        if spec.startswith("_"):
            raise exceptions.CommandError("Can't access internal attribute %s" % spec)

        part = getattr(current, spec, None)
        if i == len(path) - 1:
            if spec == "port" and is_addr(current):
                return str(current[1])
            if spec == "host" and is_addr(current):
                return str(current[0])
            elif spec.startswith("header["):
                if not current:
                    return ""
                return current.headers.get(headername(spec), "")
            elif isinstance(part, bytes):
                return part
            elif isinstance(part, bool):
                return "true" if part else "false"
            elif isinstance(part, certs.Cert):
                return part.to_pem().decode("ascii")
        current = part
    return str(current or "")


class Cut:
    @command.command("cut")
    def cut(
        self,
        flows: typing.Sequence[flow.Flow],
        cuts: mitmproxy.types.CutSpec,
    ) -> mitmproxy.types.Data:
        """
            Cut data from a set of flows. Cut specifications are attribute paths
            from the base of the flow object, with a few conveniences - "port"
            and "host" retrieve parts of an address tuple, ".header[key]"
            retrieves a header value. Return values converted to strings or
            bytes: SSL certificates are converted to PEM format, bools are "true"
            or "false", "bytes" are preserved, and all other values are
            converted to strings.
        """
        ret: typing.List[typing.List[typing.Union[str, bytes]]] = []
        for f in flows:
            ret.append([extract(c, f) for c in cuts])
        return ret  # type: ignore

    @command.command("cut.save")
    def save(
        self,
        flows: typing.Sequence[flow.Flow],
        cuts: mitmproxy.types.CutSpec,
        path: mitmproxy.types.Path
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
            epath = os.path.expanduser(path[1:])
            path = mitmproxy.types.Path(epath)
        try:
            if len(cuts) == 1 and len(flows) == 1:
                with open(path, "ab" if append else "wb") as fp:
                    if fp.tell() > 0:
                        # We're appending to a file that already exists and has content
                        fp.write(b"\n")
                    v = extract(cuts[0], flows[0])
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
        except IOError as e:
            ctx.log.error(str(e))

    @command.command("cut.clip")
    def clip(
        self,
        flows: typing.Sequence[flow.Flow],
        cuts: mitmproxy.types.CutSpec,
    ) -> None:
        """
            Send cuts to the clipboard. If there are multiple flows or cuts, the
            format is UTF-8 encoded CSV. If there is exactly one row and one
            column, the data is written to file as-is, with raw bytes preserved.
        """
        fp = io.StringIO(newline="")
        if len(cuts) == 1 and len(flows) == 1:
            v = extract(cuts[0], flows[0])
            if isinstance(v, bytes):
                fp.write(strutils.always_str(v))
            else:
                fp.write(v)
            ctx.log.alert("Clipped single cut.")
        else:
            writer = csv.writer(fp)
            for f in flows:
                vals = [extract(c, f) for c in cuts]
                writer.writerow(
                    [strutils.always_str(v) or "" for v in vals]  # type: ignore
                )
            ctx.log.alert("Clipped %s cuts as CSV." % len(cuts))
        try:
            pyperclip.copy(fp.getvalue())
        except pyperclip.PyperclipException as e:
            ctx.log.error(str(e))
