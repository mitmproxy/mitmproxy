from collections.abc import Sequence
from typing import NamedTuple
from typing import Optional

from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import http
from mitmproxy import version
from mitmproxy.net.http.status_codes import NO_RESPONSE


class BlockSpec(NamedTuple):
    """
    Specified behavior for a block request
    """
    matches: flowfilter.TFilter
    status_code: int

class AllowSpec(NamedTuple):
    """
    Specified behavior for an allow
    """
    matches: flowfilter.TFilter

def parse_blockspec(option: str) -> BlockSpec:
    """
    Parses strings in the following format, enforces number of segments:

        /flow-filter/status

    """
    sep, rem = option[0], option[1:]

    parts = rem.split(sep, 2)
    if len(parts) != 2:
        raise ValueError("Invalid number of parameters (2 are expected)")
    flow_patt, status = parts
    try:
        status_code = int(status)
    except ValueError:
        raise ValueError(f"Invalid HTTP status code: {status}")
    flow_filter = flowfilter.parse(flow_patt)

    return BlockSpec(matches=flow_filter, status_code=status_code)


class FilterList:
    def __init__(self) -> None:
        self.blocked_items: Optional[list[BlockSpec]] = []
        self.allowed_items: Optional[list[BlockSpec]] = []

    def load(self, loader):
        loader.add_option(
            "block_list",
            Sequence[str],
            [],
            """
            Block matching requests and return an empty response with the specified HTTP status.
            Option syntax is "/flow-filter/status-code", where flow-filter describes
            which requests this rule should be applied to and status-code is the HTTP status code to return for
            blocked requests. The separator ("/" in the example) can be any character.
            Setting a non-standard status code of 444 will close the connection without sending a response.
            NOTE: This option cannot be used together with `allow_list` if both options are configured, an 
            OptionsError will be raised. Configuring `blocked_items` will set `allowed_items` to None.
            """,
        )
        loader.add_option(
            "allow_list",
            Sequence[str],
            [],
            """
            Accept *only* the requests specified by the user. Any forbidden request is sent an empty response 
            with a 403 status code. Option syntax is "/flow-filter/status-code", where flow-filter describes
            which requests this rule should be applied to and status-code is the HTTP status code to return for
            blocked requests. The separator ("/" in the example) can be any character.
            Setting a non-standard status code of 444 will close the connection without sending a response.
            NOTE: This option cannot be used together with `block_list` if both options are configured, an 
            OptionsError will be raised. Configuring `allowed_items` will set `blocked_items` to None.
            """,
        loader.add_option(
            "global_errorcode",
            Optional[int],
            403,
            [],
        )
        )

    def configure(self, updated):

        if "block_list" in updated and "allow_list" in updated:
            raise exceptions.OptionsError(
                "Cannot simultaneously configure options `block_list` and `allow_list`"
            )

        if "block_list" in updated:
            self.allowed_items = None
            self.blocked_items = []
            for option in ctx.options.block_list:
                try:
                    spec = parse_spec(option)
                except ValueError as e:
                    raise exceptions.OptionsError(
                        f"Cannot parse block_list option {option}: {e}"
                    ) from e
                self.blocked_items.append(spec)

        if "allow_list" in updated:
            self.allowed_items = []
            self.blocked_items = None
            for option in ctx.options.allow_list:
                try:
                    spec = parse_spec(option)
                except ValueError as e:
                    raise exceptions.OptionsError(
                        f"Cannot parse block_list option {option}: {e}"
                    ) from e
                self.allowed_items.append(spec)

    def request(self, flow: http.HTTPFlow) -> None:
        if flow.response or flow.error or not flow.live:
            return
        
        if self.blocked_items != None:
            for spec in self.blocked_items:
                if spec.matches(flow):
                    flow.metadata["blocklisted"] = True
                    if spec.status_code == NO_RESPONSE:
                        flow.kill()
                    else:
                        flow.response = http.Response.make(
                            spec.status_code, headers={"Server": version.MITMPROXY}
                        )
        
        if self.allowed_items != None:
            global go_thru
            go_thru = False
            for spec in self.allowed_items:
                if spec.matches(flow):
                    go_thru = True
                    break
            if go_thru == False:
                flow.metadata["blocklisted"] = True
                if spec.status_code == NO_RESPONSE:
                    flow.kill()
                else:
                    flow.response = http.Response.make(
                        spec.status_code, headers={"Server": version.MITMPROXY}
                        )
