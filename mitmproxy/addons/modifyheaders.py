import typing

from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import ctx


def parse_modify_headers(s):
    """
        Returns a (flow_filter, header_name, header_value) tuple.

        The general form for a modify_headers hook is as follows:

            [/flow_filter]/header_name/header_value

        The first character specifies the separator. Example:

            :~q:foo:bar

        If only two clauses are specified, the pattern is set to match
        universally (i.e. ".*"). Example:

            /foo/bar

        Clauses are parsed from left to right. Extra separators are taken to be
        part of the final clause. For instance, the replacement clause below is
        "foo/bar/":

            /one/two/foo/bar/
    """
    sep, rem = s[0], s[1:]
    parts = rem.split(sep, 2)
    if len(parts) == 2:
        flow_filter = ".*"
        header_name, header_value = parts
    elif len(parts) == 3:
        flow_filter, header_name, header_value = parts
    else:
        raise exceptions.OptionsError(
            "Invalid modify_headers specifier: %s" % s
        )
    return flow_filter, header_name, header_value


class ModifyHeaders:
    def __init__(self):
        self.lst = []

    def load(self, loader):
        loader.add_option(
            "modify_headers", typing.Sequence[str], [],
            """
            Header modify pattern of the form "[/flow-filter]/header-name/header-value", where the
            separator can be any character. An empty header-value removes existing header-name headers.
            """
        )

    def configure(self, updated):
        if "modify_headers" in updated:
            self.lst = []
            for shead in ctx.options.modify_headers:
                flow_pattern, header, value = parse_modify_headers(shead)

                flow_filter = flowfilter.parse(flow_pattern)
                if not flow_filter:
                    raise exceptions.OptionsError(
                        "Invalid modify_headers flow filter %s" % flow_pattern
                    )
                self.lst.append((flow_pattern, flow_filter, header, value))

    def run(self, f, hdrs):
        for _, flow_filter, header, value in self.lst:
            if flow_filter(f):
                hdrs.pop(header, None)
        for _, flow_filter, header, value in self.lst:
            if flow_filter(f) and value:
                hdrs.add(header, value)

    def request(self, flow):
        if not flow.reply.has_message:
            self.run(flow, flow.request.headers)

    def response(self, flow):
        if not flow.reply.has_message:
            self.run(flow, flow.response.headers)
