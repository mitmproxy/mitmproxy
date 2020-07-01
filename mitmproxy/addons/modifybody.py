import os
import re
import typing

from mitmproxy import exceptions
from mitmproxy import ctx
from mitmproxy.addons.modifyheaders import parse_modify_spec, ModifySpec


class ModifyBody:
    def __init__(self):
        self.replacements: typing.List[ModifySpec] = []

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
        if "modify_body" in updated:
            self.replacements = []
            for option in ctx.options.modify_body:
                try:
                    spec = parse_modify_spec(option)
                    try:
                        re.compile(spec.subject)
                    except re.error:
                        raise ValueError(f"Invalid regular expression: {spec.subject}")
                except ValueError as e:
                    raise exceptions.OptionsError(
                        f"Cannot parse modify_body option {option}: {e}"
                    ) from e

                self.replacements.append(spec)

    def run(self, flow):
        for spec in self.replacements:
            if spec.matches(flow):
                if flow.response:
                    self.replace(flow.response, spec.subject, spec.replacement)
                else:
                    self.replace(flow.request, spec.subject, spec.replacement)

    def request(self, flow):
        if not flow.reply.has_message:
            self.run(flow)

    def response(self, flow):
        if not flow.reply.has_message:
            self.run(flow)

    def replace(self, obj, search, repl):
        """
        Replaces all matches of the regex search in the body of the message with repl.

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
