import logging
import re
from collections.abc import Sequence

from mitmproxy import ctx, exceptions
from mitmproxy.addons.modifyheaders import parse_modify_spec, ModifySpec


class ModifyBody:
    def __init__(self):
        self.replacements: list[ModifySpec] = []

    def load(self, loader):
        loader.add_option(
            "modify_body",
            Sequence[str],
            [],
            """
            Replacement pattern of the form "[/flow-filter]/regex/[@]replacement", where
            the separator can be any character. The @ allows to provide a file path that
            is used to read the replacement string.
            """,
        )

    def configure(self, updated):
        if "modify_body" in updated:
            self.replacements = []
            for option in ctx.options.modify_body:
                try:
                    spec = parse_modify_spec(option, True)
                except ValueError as e:
                    raise exceptions.OptionsError(
                        f"Cannot parse modify_body option {option}: {e}"
                    ) from e

                self.replacements.append(spec)

    def request(self, flow):
        if flow.response or flow.error or not flow.live:
            return
        self.run(flow)

    def response(self, flow):
        if flow.error or not flow.live:
            return
        self.run(flow)

    def run(self, flow):
        for spec in self.replacements:
            if spec.matches(flow):
                try:
                    replacement = spec.read_replacement()
                except OSError as e:
                    logging.warning(f"Could not read replacement file: {e}")
                    continue
                if flow.response:
                    flow.response.content = re.sub(
                        spec.subject,
                        replacement,
                        flow.response.content,
                        flags=re.DOTALL,
                    )
                else:
                    flow.request.content = re.sub(
                        spec.subject, replacement, flow.request.content, flags=re.DOTALL
                    )
