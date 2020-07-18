import re
import typing

from mitmproxy import ctx, exceptions, flowfilter, http
from mitmproxy.utils.spec import parse_spec


class MapRemoteSpec(typing.NamedTuple):
    matches: flowfilter.TFilter
    subject: str
    replacement: str


def parse_map_remote_spec(option: str) -> MapRemoteSpec:
    spec = MapRemoteSpec(*parse_spec(option))

    try:
        re.compile(spec.subject)
    except re.error as e:
        raise ValueError(f"Invalid regular expression {spec.subject!r} ({e})")

    return spec


class MapRemote:
    def __init__(self):
        self.replacements: typing.List[MapRemoteSpec] = []

    def load(self, loader):
        loader.add_option(
            "map_remote", typing.Sequence[str], [],
            """
            Map remote resources to another remote URL using a pattern of the form
            "[/flow-filter]/url-regex/replacement", where the separator can
            be any character.
            """
        )

    def configure(self, updated):
        if "map_remote" in updated:
            self.replacements = []
            for option in ctx.options.map_remote:
                try:
                    spec = parse_map_remote_spec(option)
                except ValueError as e:
                    raise exceptions.OptionsError(f"Cannot parse map_remote option {option}: {e}") from e

                self.replacements.append(spec)

    def request(self, flow: http.HTTPFlow) -> None:
        if flow.reply and flow.reply.has_message:
            return
        for spec in self.replacements:
            if spec.matches(flow):
                url = flow.request.pretty_url
                new_url = re.sub(spec.subject, spec.replacement, url)
                # this is a bit messy: setting .url also updates the host header,
                # so we really only do that if the replacement affected the URL.
                if url != new_url:
                    flow.request.url = new_url
