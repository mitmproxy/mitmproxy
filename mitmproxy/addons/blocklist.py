import typing
import mimetypes

from mitmproxy import ctx, exceptions, flowfilter, http, version
from mitmproxy.net.http.status_codes import RESPONSES


class BlockListSpec(typing.NamedTuple):
    matches: flowfilter.TFilter
    block_type: str
    status: str


class BlockList:
    def __init__(self):
        self.replacements: typing.List[BlockListSpec] = []

    def load(self, loader):
        loader.add_option(
            "block_list", typing.Sequence[str], [],
            """
            Block matching requests and return an empty response with the specified HTTP status.
            Option is formatted as "[:flow-filter:(block|allow-only):status]", where the
            separator can be any character. allow-only allows only matching traffic to be unaffected,
            block will block only matching traffic.
            HTTP status is the HTTP status code to return for blocked requests.
            Note: Status code 444 is special-cased and will close the connection without sending a response.
            """
        )

    def configure(self, updated):
        if "block_list" in updated:
            self.block_list_items = []
            for option in ctx.options.block_list:
                try:
                    spec = self.__parse_blocklist_spec(option)
                except ValueError as e:
                    raise exceptions.OptionsError(f"Cannot parse block_list option {option}: {e}") from e

                self.block_list_items.append(spec)

    def request(self, flow: http.HTTPFlow) -> None:
        if flow.response or flow.error or (flow.reply and flow.reply.state == "taken"):
            return

        for spec in self.block_list_items:
            matching = spec.matches(flow)
            if (matching and spec.block_type == 'block') or (not matching and spec.block_type == 'allow-only'):
                self.__block_it(flow, spec)

    def __block_it(self, flow, spec):
        status = int(spec.status)
        if status == 444:
            flow.kill()
        else:
            headers = {"Server": version.MITMPROXY}
            mimetype = mimetypes.guess_type(flow.request.url)[0]
            if mimetype:
                headers["Content-Type"] = mimetype
            flow.response = http.Response.make(
                status,
                headers=headers
            )
        return

    def __parse_blocklist_spec(self, option: str) -> typing.Tuple[flowfilter.TFilter, str, str]:
        """
        Parses strings in the following format, enforces number of segments:

            [/flow-filter]/(block|allow-only)/status

        """
        sep, rem = option[0], option[1:]
        parts = rem.lower().split(sep, 2)
        if len(parts) == 3:
            flow_patt, block_type, status = parts
            flow_filter = flowfilter.parse(flow_patt)
            if not flow_filter:
                raise ValueError(f"Invalid filter pattern: {flow_patt}")
            if block_type not in ('block', 'allow-only'):
                raise ValueError(f"Invalid block type. Must be `allow-only` or `block`")
            if not RESPONSES.get(int(status)):
                raise ValueError(f"Invalid HTTP status code: {status}")
        else:
            raise ValueError("Invalid number of parameters (3 are expected)")
        return BlockListSpec(matches=flow_filter, block_type=block_type, status=status)
