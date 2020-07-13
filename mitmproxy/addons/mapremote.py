import re
import typing

from mitmproxy import exceptions, http
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
                    spec = parse_modify_spec(option, True)
                except ValueError as e:
                    raise exceptions.OptionsError(f"Cannot parse map_remote option {option}: {e}") from e

                self.replacements.append(spec)

    def request(self, flow: http.HTTPFlow) -> None:
        if flow.reply and flow.reply.has_message:
            return
        for spec in self.replacements:
            if spec.matches(flow):
                try:
                    replacement = spec.read_replacement()
                except IOError as e:
                    ctx.log.warn(f"Could not read replacement file: {e}")
                    continue

                url = flow.request.pretty_url.encode("utf8", "surrogateescape")
                new_url = re.sub(spec.subject, replacement, url)
                # this is a bit messy: setting .url also updates the host header,
                # so we really only do that if the replacement affected the URL.
                if url != new_url:
                    flow.request.url = new_url
