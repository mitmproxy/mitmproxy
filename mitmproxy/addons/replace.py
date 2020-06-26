import os
import re
import typing

from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import ctx
from mitmproxy.utils import strutils


def parse_replacements(s):
    """
        Returns a (flow_filter, regex, replacement) tuple.

        The general form for a replacements hook is as follows:

            [/flow_filter]/regex/replacement

        The first character specifies the separator. Example:

            :~q:foo:bar

        If only two clauses are specified, the pattern is set to match
        universally (i.e. ".*"). Example:

            /foo/bar

        Clauses are parsed from left to right. Extra separators are taken to be
        part of the final clause. For instance, the replacement clause below is
        "foo/bar/":

            /one/two/foo/bar/
    """
    sep, rem = s[0], s[1:]
    parts = rem.split(sep, 2)
    if len(parts) == 2:
        flow_filter = ".*"
        regex, repl = parts
    elif len(parts) == 3:
        flow_filter, regex, repl = parts
    else:
        raise exceptions.OptionsError(
            "Invalid replacements specifier: %s" % s
        )
    return flow_filter, regex, repl


class Replace:
    def __init__(self):
        self.lst = []

    def load(self, loader):
        loader.add_option(
            "replacements", typing.Sequence[str], [],
            """
            Replacement pattern of the form "[/flow-filter]/regex/replacement", where
            the separator can be any character.
            """
        )

    def configure(self, updated):
        """
            .replacements is a list of tuples (flow_filter_pattern, regex, repl):

            flow_filter_pattern: a string specifying a flow filter pattern.
            regex: a regular expression, as string.
            repl: the replacement string
        """
        if "replacements" in updated:
            lst = []
            for rep in ctx.options.replacements:
                flow_filter_pattern, regex, repl = parse_replacements(rep)

                flow_filter = flowfilter.parse(flow_filter_pattern)
                if not flow_filter:
                    raise exceptions.OptionsError(
                        "Invalid replacements flow filter: %s" % flow_filter_pattern
                    )
                try:
                    # We should ideally escape here before trying to compile
                    re.compile(regex)
                except re.error as e:
                    raise exceptions.OptionsError(
                        "Invalid regular expression: %s - %s" % (regex, str(e))
                    )
                if repl.startswith("@") and not os.path.isfile(repl[1:]):
                    raise exceptions.OptionsError(
                        "Invalid file path: {}".format(repl[1:])
                    )
                lst.append((regex, repl, flow_filter))
            self.lst = lst

    def execute(self, f):
        for regex, repl, flow_filter in self.lst:
            if flow_filter(f):
                if f.response:
                    self.replace(f.response, regex, repl)
                else:
                    self.replace(f.request, regex, repl)

    def request(self, flow):
        if not flow.reply.has_message:
            self.execute(flow)

    def response(self, flow):
        if not flow.reply.has_message:
            self.execute(flow)

    def replace(self, obj, search, repl):
        """
        Replaces a regular expression pattern with repl in the body of the message.
        Encoded body will be decoded before replacement, and re-encoded afterwards.

        Returns:
            The number of replacements made.
        """
        if repl.startswith("@"):
            repl = os.path.expanduser(repl[1:])
            try:
                with open(repl, "rb") as f:
                    repl = f.read()
            except IOError:
                ctx.log.warn("Could not read replacement file: %s" % repl)
                return

        if isinstance(search, str):
            search = strutils.escaped_str_to_bytes(search)
        if isinstance(repl, str):
            repl = strutils.escaped_str_to_bytes(repl)
        replacements = 0
        if obj.content:
            obj.content, replacements = re.subn(search, repl, obj.content, flags=re.DOTALL)
        return replacements
