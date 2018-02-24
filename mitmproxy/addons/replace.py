import os
import re
import typing

from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import ctx


def parse_hook(s):
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


class Replace:
    def __init__(self):
        self.lst = []

    def load(self, loader):
        loader.add_option(
            "replacements", typing.Sequence[str], [],
            """
            Replacement patterns of the form "/pattern/regex/replacement", where
            the separator can be any character.
            """
        )

    def configure(self, updated):
        """
            .replacements is a list of tuples (fpat, rex, s):

            fpatt: a string specifying a filter pattern.
            rex: a regular expression, as string.
            s: the replacement string
        """
        if "replacements" in updated:
            lst = []
            for rep in ctx.options.replacements:
                fpatt, rex, s = parse_hook(rep)

                flt = flowfilter.parse(fpatt)
                if not flt:
                    raise exceptions.OptionsError(
                        "Invalid filter pattern: %s" % fpatt
                    )
                try:
                    # We should ideally escape here before trying to compile
                    re.compile(rex)
                except re.error as e:
                    raise exceptions.OptionsError(
                        "Invalid regular expression: %s - %s" % (rex, str(e))
                    )
                if s.startswith("@") and not os.path.isfile(s[1:]):
                    raise exceptions.OptionsError(
                        "Invalid file path: {}".format(s[1:])
                    )
                lst.append((rex, s, flt))
            self.lst = lst

    def execute(self, f):
        for rex, s, flt in self.lst:
            if flt(f):
                if f.response:
                    self.replace(f.response, rex, s)
                else:
                    self.replace(f.request, rex, s)

    def request(self, flow):
        if not flow.reply.has_message:
            self.execute(flow)

    def response(self, flow):
        if not flow.reply.has_message:
            self.execute(flow)

    def replace(self, obj, rex, s):
        if s.startswith("@"):
            s = os.path.expanduser(s[1:])
            try:
                with open(s, "rb") as f:
                    s = f.read()
            except IOError:
                ctx.log.warn("Could not read replacement file: %s" % s)
                return
        obj.replace(rex, s, flags=re.DOTALL)
