import re

from mitmproxy import exceptions
from mitmproxy import flowfilter


class Replace:
    def __init__(self):
        self.lst = []

    def configure(self, options, updated):
        """
            .replacements is a list of tuples (fpat, rex, s):

            fpatt: a string specifying a filter pattern.
            rex: a regular expression, as bytes.
            s: the replacement string, as bytes
        """
        lst = []
        for fpatt, rex, s in options.replacements:
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
                    f.response.replace(rex, s, flags=re.DOTALL)
                else:
                    f.request.replace(rex, s, flags=re.DOTALL)

    def request(self, flow):
        if not flow.reply.has_message:
            self.execute(flow)

    def response(self, flow):
        if not flow.reply.has_message:
            self.execute(flow)
