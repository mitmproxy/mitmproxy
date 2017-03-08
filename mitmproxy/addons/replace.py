import re

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


class _ReplaceBase:
    def __init__(self):
        self.lst = []

    def configure(self, options, updated):
        """
            .replacements is a list of tuples (fpat, rex, s):

            fpatt: a string specifying a filter pattern.
            rex: a regular expression, as bytes.
            s: the replacement string, as bytes
        """
        if self.optionName in updated:
            lst = []
            for rep in getattr(options, self.optionName):
                fpatt, rex, s = parse_hook(rep)

                flt = flowfilter.parse(fpatt)
                if not flt:
                    raise exceptions.OptionsError(
                        "Invalid filter pattern: %s" % fpatt
                    )
                try:
                    re.compile(rex)
                except re.error as e:
                    raise exceptions.OptionsError(
                        "Invalid regular expression: %s - %s" % (rex, str(e))
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


class Replace(_ReplaceBase):
    optionName = "replacements"

    def replace(self, obj, rex, s):
        obj.replace(rex, s, flags=re.DOTALL)


class ReplaceFile(_ReplaceBase):
    optionName = "replacement_files"

    def replace(self, obj, rex, s):
        try:
            v = open(s, "rb").read()
        except IOError as e:
            ctx.log.warn("Could not read replacement file: %s" % s)
            return
        obj.replace(rex, v, flags=re.DOTALL)
