import typing

from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import ctx


def parse_setheader(s):
    """
        Returns a (header_name, header_value, flow_filter) tuple.

        The general form for a setheader hook is as follows:

            /header_name/header_value/flow_filter

        The first character specifies the separator. Example:

            :foo:bar:~q
        
        If only two clauses are specified, the pattern is set to match
        universally (i.e. ".*"). Example:

            /foo/bar/

        Clauses are parsed from left to right. Extra separators are taken to be
        part of the final clause. For instance, the flow filter below is
        "foo/bar/":

            /one/two/foo/bar/
    """
    sep, rem = s[0], s[1:]
    parts = rem.split(sep, 2)
    if len(parts) == 2:
        flow_filter = ".*"
        header_name, header_value = parts
    elif len(parts) == 3:
        header_name, header_value, flow_filter = parts
    else:
        raise exceptions.OptionsError(
            "Invalid replacement specifier: %s" % s
        )
    return header_name, header_value, flow_filter


class SetHeaders:
    def __init__(self):
        self.lst = []

    def load(self, loader):
        loader.add_option(
            "setheaders", typing.Sequence[str], [],
            """
            Header set pattern of the form "/header-name/header-value[/flow-filter]", where the
            separator can be any character. An empty header-value removes existing header-name headers.
            """
        )

    def configure(self, updated):
        if "setheaders" in updated:
            self.lst = []
            for shead in ctx.options.setheaders:
                header, value, flow_pattern = parse_setheader(shead)

                flow_filter = flowfilter.parse(flow_pattern)
                if not flow_filter:
                    raise exceptions.OptionsError(
                        "Invalid setheader filter pattern %s" % flow_pattern
                    )
                self.lst.append((header, value, flow_pattern, flow_filter))

    def run(self, f, hdrs):
        for header, value, _, flow_filter in self.lst:
            if flow_filter(f):
                hdrs.pop(header, None)
        for header, value, _, flow_filter in self.lst:
            if flow_filter(f) and value:
                hdrs.add(header, value)

    def request(self, flow):
        if not flow.reply.has_message:
            self.run(flow, flow.request.headers)

    def response(self, flow):
        if not flow.reply.has_message:
            self.run(flow, flow.response.headers)
