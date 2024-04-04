import csv
import io
import logging
import os.path
from collections.abc import Sequence
from typing import Any

import pyperclip

import mitmproxy.types
from mitmproxy import certs
from mitmproxy import command
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import http
from mitmproxy.log import ALERT

logger = logging.getLogger(__name__)


def headername(spec: str):
    if not (spec.startswith("header[") and spec.endswith("]")):
        raise exceptions.CommandError("Invalid header spec: %s" % spec)
    return spec[len("header[") : -1].strip()


def is_addr(v):
    return isinstance(v, tuple) and len(v) > 1


def extract(cut: str, f: flow.Flow) -> str | bytes:
    # Hack for https://github.com/mitmproxy/mitmproxy/issues/6721:
    # Make "save body" keybind work for WebSocket flows.
    # Ideally the keybind would be smarter and this here can get removed.
    if (
        isinstance(f, http.HTTPFlow)
        and f.websocket
        and cut in ("request.content", "response.content")
    ):
        return f.websocket._get_formatted_messages()

    path = cut.split(".")
    current: Any = f
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
            elif isinstance(part, certs.Cert):  # pragma: no cover
                return part.to_pem().decode("ascii")
            elif (
                isinstance(part, list)
                and len(part) > 0
                and isinstance(part[0], certs.Cert)
            ):
                # TODO: currently this extracts only the very first cert as PEM-encoded string.
                return part[0].to_pem().decode("ascii")
        current = part
    return str(current or "")


def extract_str(cut: str, f: flow.Flow) -> str:
    ret = extract(cut, f)
    if isinstance(ret, bytes):
        return repr(ret)
    else:
        return ret


class Cut:
    @command.command("cut")
    def cut(
        self,
        flows: Sequence[flow.Flow],
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
        ret: list[list[str | bytes]] = []
        for f in flows:
            ret.append([extract(c, f) for c in cuts])
        return ret  # type: ignore

    @command.command("cut.save")
    def save(
        self,
        flows: Sequence[flow.Flow],
        cuts: mitmproxy.types.CutSpec,
        path: mitmproxy.types.Path,
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
                logger.log(ALERT, "Saved single cut.")
            else:
                with open(
                    path, "a" if append else "w", newline="", encoding="utf8"
                ) as tfp:
                    writer = csv.writer(tfp)
                    for f in flows:
                        vals = [extract_str(c, f) for c in cuts]
                        writer.writerow(vals)
                logger.log(
                    ALERT,
                    "Saved %s cuts over %d flows as CSV." % (len(cuts), len(flows)),
                )
        except OSError as e:
            logger.error(str(e))

    @command.command("cut.clip")
    def clip(
        self,
        flows: Sequence[flow.Flow],
        cuts: mitmproxy.types.CutSpec,
    ) -> None:
        """
        Send cuts to the clipboard. If there are multiple flows or cuts, the
        format is UTF-8 encoded CSV. If there is exactly one row and one
        column, the data is written to file as-is, with raw bytes preserved.
        """
        v: str | bytes
        fp = io.StringIO(newline="")
        if len(cuts) == 1 and len(flows) == 1:
            v = extract_str(cuts[0], flows[0])
            fp.write(v)
            logger.log(ALERT, "Clipped single cut.")
        else:
            writer = csv.writer(fp)
            for f in flows:
                vals = [extract_str(c, f) for c in cuts]
                writer.writerow(vals)
            logger.log(ALERT, "Clipped %s cuts as CSV." % len(cuts))
        try:
            pyperclip.copy(fp.getvalue())
        except pyperclip.PyperclipException as e:
            logger.error(str(e))
