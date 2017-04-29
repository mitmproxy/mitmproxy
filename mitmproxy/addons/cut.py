import os
import typing
from mitmproxy import command
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import ctx
from mitmproxy.utils import strutils


def headername(spec: str):
    if not (spec.startswith("header[") and spec.endswith("]")):
        raise exceptions.CommandError("Invalid header spec: %s" % spec)
    return spec[len("header["):-1].strip()


def extract(cut: str, f: flow.Flow) -> typing.Union[str, bytes]:
    if cut.startswith("q."):
        req = getattr(f, "request", None)
        if not req:
            return ""
        rem = cut[len("q."):]
        if rem in ["method", "scheme", "host", "port", "path", "url"]:
            return str(getattr(req, rem))
        elif rem == "content":
            return req.content
        elif rem.startswith("header["):
            return req.headers.get(headername(rem), "")
    elif cut.startswith("s."):
        resp = getattr(f, "response", None)
        if not resp:
            return ""
        rem = cut[len("s."):]
        if rem in ["status_code", "reason"]:
            return str(getattr(resp, rem))
        elif rem == "content":
            return resp.content
        elif rem.startswith("header["):
            return resp.headers.get(headername(rem), "")
    raise exceptions.CommandError("Invalid cut specification: %s" % cut)


def parse_cutspec(s: str) -> typing.Tuple[str, typing.Sequence[str]]:
    """
        Returns (flowspec, [cuts]).

        Raises exceptions.CommandError if input is invalid.
    """
    parts = s.split("|", maxsplit=1)
    flowspec = "@all"
    if len(parts) == 2:
        flowspec = parts[1].strip()
    cuts = parts[0]
    cutparts = [i.strip() for i in cuts.split(",") if i.strip()]
    if len(cutparts) == 0:
        raise exceptions.CommandError("Invalid cut specification.")
    return flowspec, cutparts


class Cut:
    @command.command("cut")
    def cut(self, cutspec: str) -> command.Cuts:
        """
            Resolve a cut specification of the form "cuts|flowspec". The
            flowspec is optional, and if it is not specified, it is assumed to
            be @all. The cuts are a comma-separated list of cut snippets.

            HTTP requests: q.method, q.scheme, q.host, q.port, q.path, q.url,
            q.header[key], q.content

            HTTP responses: s.status_code, s.reason, s.header[key], s.content

            Client connections: cc.address, cc.sni, cc.cipher_name,
            cc.alpn_proto, cc.tls_version

            Server connections: sc.address, sc.ip, sc.cert, sc.sni,
            sc.alpn_proto, sc.tls_version
        """
        flowspec, cuts = parse_cutspec(cutspec)
        flows = ctx.master.commands.call_args("view.resolve", [flowspec])
        ret = []
        for f in flows:
            ret.append([extract(c, f) for c in cuts])
        return ret

    @command.command("cut.save")
    def save(self, cuts: command.Cuts, path: str) -> None:
        """
            Save cuts to file.

                cut.save resp.content|@focus /tmp/foo

                cut.save req.host,resp.header[content-type]|@focus /tmp/foo
        """
        mode = "wb"
        if path.startswith("+"):
            mode = "ab"
            path = path[1:]
        path = os.path.expanduser(path)
        with open(path, mode) as fp:
            if fp.tell() > 0:
                # We're appending to a file that already exists and has content
                fp.write(b"\n")
            for ci, c in enumerate(cuts):
                if ci > 0:
                    fp.write(b"\n")
                for vi, v in enumerate(c):
                    if vi > 0:
                        fp.write(b", ")
                    if isinstance(v, str):
                        v = strutils.always_bytes(v)
                    fp.write(v)
        ctx.log.alert("Saved %s cuts." % len(cuts))
