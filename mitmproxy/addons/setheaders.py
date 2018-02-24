import typing

from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import ctx


def parse_setheader(s):
    """
        Returns a (pattern, regex, replacement) tuple.

        The general form for a replacement hook is as follows:

            /patt/regex/replacement

        The first character specifies the separator. Example:

            :~q:foo:bar

        If only two clauses are specified, the pattern is set to match
        universally (i.e. ".*"). Example:

            /foo/bar/

        Clauses are parsed from left to right. Extra separators are taken to be
        part of the final clause. For instance, the replacement clause below is
        "foo/bar/":

            /one/two/foo/bar/
    """
    sep, rem = s[0], s[1:]
    parts = rem.split(sep, 2)
    if len(parts) == 2:
        patt = ".*"
        a, b = parts
    elif len(parts) == 3:
        patt, a, b = parts
    else:
        raise exceptions.OptionsError(
            "Invalid replacement specifier: %s" % s
        )
    return patt, a, b


class SetHeaders:
    def __init__(self):
        self.lst = []

    def load(self, loader):
        loader.add_option(
            "setheaders", typing.Sequence[str], [],
            """
            Header set pattern of the form "/pattern/header/value", where the
            separator can be any character.
            """
        )

    def configure(self, updated):
        if "setheaders" in updated:
            self.lst = []
            for shead in ctx.options.setheaders:
                fpatt, header, value = parse_setheader(shead)

                flt = flowfilter.parse(fpatt)
                if not flt:
                    raise exceptions.OptionsError(
                        "Invalid setheader filter pattern %s" % fpatt
                    )
                self.lst.append((fpatt, header, value, flt))

    def run(self, f, hdrs):
        for _, header, value, flt in self.lst:
            if flt(f):
                hdrs.pop(header, None)
        for _, header, value, flt in self.lst:
            if flt(f):
                hdrs.add(header, value)

    def request(self, flow):
        if not flow.reply.has_message:
            self.run(flow, flow.request.headers)

    def response(self, flow):
        if not flow.reply.has_message:
            self.run(flow, flow.response.headers)
