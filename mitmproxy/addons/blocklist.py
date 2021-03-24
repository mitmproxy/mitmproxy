import typing
import mimetypes

from mitmproxy import ctx, exceptions, flowfilter, http, version
from mitmproxy.net.http.status_codes import RESPONSES
from mitmproxy.net.http.status_codes import NO_RESPONSE


class BlockListSpec(typing.NamedTuple):
    matches: flowfilter.TFilter
    status: int


class BlockList:
    def __init__(self):
        self.block_list_items: typing.List[BlockListSpec] = []

    def load(self, loader):
        loader.add_option(
            "block_list", typing.Sequence[str], [],
            """
            Block matching requests and return an empty response with the specified HTTP status.
            Option is formatted as "[:flow-filter:status]", where the separator can be any character.
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
            if spec.matches(flow):
                self.__block_it(flow, spec)

    def __block_it(self, flow, spec):
        status = spec.status
        if status == NO_RESPONSE:
            flow.kill()
        else:
            headers = {"Server": version.MITMPROXY}
            # Give JS browser callbacks expected content type even though the request is empty
            mimetype = mimetypes.guess_type(flow.request.url)[0]
            if mimetype:
                headers["Content-Type"] = mimetype
            flow.response = http.Response.make(
                status,
                headers=headers
            )
        return

    def __parse_blocklist_spec(self, option: str) -> BlockListSpec:
        """
        Parses strings in the following format, enforces number of segments:

            [/flow-filter]/status

        """
        sep, rem = option[0], option[1:]
        parts = rem.lower().split(sep, 2)
        if len(parts) != 2:
            raise ValueError("Invalid number of parameters (2 are expected)")
        flow_patt, status = parts
        status_code = int(status)
        flow_filter = flowfilter.parse(flow_patt)
        if not flow_filter:
            raise ValueError(f"Invalid filter pattern: {flow_patt}")
        if not RESPONSES.get(status_code):
            raise ValueError(f"Invalid HTTP status code: {status}")

        return BlockListSpec(matches=flow_filter, status=status_code)
