import re
import typing
import mimetypes

from mitmproxy import ctx, exceptions, flowfilter, http, version
from mitmproxy.utils.spec import parse_spec

class BlockListSpec(typing.NamedTuple):
    matches: flowfilter.TFilter
    regex: str
    status_code: int

def parse_block_list_spec(option: str) -> BlockListSpec:
    filter, regex, status = parse_spec(option)

    try:
        re.compile(regex)
    except re.error as e:
        raise ValueError(f"Invalid regular expression {regex!r} ({e})")

    try:
        status_code = int(status)
    except:
        raise ValueError(f"Invalid HTTP status code {status!s}")

    return BlockListSpec(filter, regex, status_code)


class BlockList:
    def __init__(self):
        self.replacements: typing.List[BlockListSpec] = []

    def load(self, loader):
        loader.add_option(
            "block_list", typing.Sequence[str], [],
            """
            Block request and instead return a Response with a hard-coded HTTP statuses.
            """
        )

    def configure(self, updated):
        if "block_list" in updated:
            self.replacements = []
            for option in ctx.options.block_list:
                try:
                    spec = parse_block_list_spec(option)
                except ValueError as e:
                    raise exceptions.OptionsError(f"Cannot parse block_list option {option}: {e}") from e

                self.replacements.append(spec)

    def request(self, flow: http.HTTPFlow) -> None:
        if flow.response or flow.error or (flow.reply and flow.reply.state == "taken"):
            return

        url = flow.request.pretty_url

        headers = {
            "Server": version.MITMPROXY
        }

        mimetype = mimetypes.guess_type(flow.request.url)[0]
        if mimetype:
            headers["Content-Type"] = mimetype

        for spec in self.replacements:
            if spec.matches(flow) and re.search(spec.regex, url):
                    flow.response = http.Response.make(
                                    spec.status_code,
                                    headers=headers
                    )
                    # only set flow.response once, for the first matching rule
                    return
