import os
import re
import typing

from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import ctx
from mitmproxy.addons.modifyheaders import parse_modify_hook


class ModifyBody:
    def __init__(self):
        self.lst = []

    def load(self, loader):
        loader.add_option(
            "modify_body", typing.Sequence[str], [],
            """
            Replacement pattern of the form "[/flow-filter]/regex/[@]replacement", where
            the separator can be any character. The @ allows to provide a file path that
            is used to read the replacement string.
            """
        )

    def configure(self, updated):
        """
            .modify_body is a list of tuples (flow_filter_pattern, regex, repl):

            flow_filter_pattern: a string specifying a flow filter pattern.
            regex: a regular expression, as string.
            repl: the replacement string
        """
        if "modify_body" in updated:
            lst = []
            for rep in ctx.options.modify_body:
                try:
                    flow_filter_pattern, regex, repl = parse_modify_hook(rep)
                except ValueError as e:
                    raise exceptions.OptionsError(
                        "Invalid modify_body option: %s" % rep
                    ) from e

                flow_filter = flowfilter.parse(flow_filter_pattern)
                if not flow_filter:
                    raise exceptions.OptionsError(
                        "Invalid modify_body flow filter: %s" % flow_filter_pattern
                    )
                try:
                    # We should ideally escape here before trying to compile
                    re.compile(regex)
                except re.error as e:
                    raise exceptions.OptionsError(
                        "Invalid regular expression: %s - %s" % (regex, str(e))
                    )
                if repl.startswith(b"@") and not os.path.isfile(repl[1:]):
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
        if repl.startswith(b"@"):
            repl = os.path.expanduser(repl[1:])
            try:
                with open(repl, "rb") as f:
                    repl = f.read()
            except IOError:
                ctx.log.warn("Could not read replacement file: %s" % repl)
                return

        replacements = 0
        if obj.content:
            obj.content, replacements = re.subn(search, repl, obj.content, flags=re.DOTALL)
        return replacements
