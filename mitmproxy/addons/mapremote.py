import os
import re
import typing

from mitmproxy import exceptions
from mitmproxy import ctx
from mitmproxy.addons.modifyheaders import parse_modify_spec, ModifySpec


class MapRemote:
    def __init__(self):
        self.replacements: typing.List[ModifySpec] = []

    def load(self, loader):
        loader.add_option(
            "map_remote", typing.Sequence[str], [],
            """
            Replacement pattern of the form "[/flow-filter]/regex/[@]replacement", where
            the separator can be any character. The @ allows to provide a file path that
            is used to read the replacement string.
            """
        )

    def configure(self, updated):
        if "map_remote" in updated:
            self.replacements = []
            for option in ctx.options.map_remote:
                try:
                    spec = parse_modify_spec(option)
                    try:
                        re.compile(spec.subject)
                    except re.error:
                        raise ValueError(f"Invalid regular expression: {spec.subject}")
                except ValueError as e:
                    raise exceptions.OptionsError(
                        f"Cannot parse map_remote option {option}: {e}"
                    ) from e

                self.replacements.append(spec)

    def request(self, flow):
        if not flow.reply.has_message:
            for spec in self.replacements:
                if spec.matches(flow):
                    self.replace(flow.request, spec.subject, spec.replacement)

    def replace(self, obj, search, repl):
        """
        Replaces all matches of the regex search in the url of the request with repl.

        Returns:
            The number of replacements made.
        """
        if repl.startswith(b"@"):
            path = os.path.expanduser(repl[1:])
            try:
                with open(path, "rb") as f:
                    repl = f.read()
            except IOError:
                ctx.log.warn("Could not read replacement file: %s" % repl)
                return

        replacements = 0
        obj.url, replacements = re.subn(search, repl, obj.pretty_url.encode("utf8", "surrogateescape"), flags=re.DOTALL)
        return replacements
