import os
import typing

from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy.utils import strutils
from mitmproxy import ctx


class ModifySpec(typing.NamedTuple):
    """
        match_str: a string specifying a flow filter pattern.
        matches: the parsed match_str as a flowfilter.TFilter object
        subject: a header name for ModifyHeaders and a regex pattern for ModifyBody
        replacement: the replacement string
    """
    match_str: str
    matches: flowfilter.TFilter
    subject: bytes
    replacement: bytes


def parse_modify_spec(option) -> ModifySpec:
    """
        The form for the modify_* options is as follows:

            * modify_headers: [/flow-filter]/header-name/[@]header-value
            * modify_body: [/flow-filter]/search-regex/[@]replace

        The @ allows to provide a file path that is used to read the respective option.
        Both ModifyHeaders and ModifyBody use ModifySpec to represent a single rule.

        The first character specifies the separator. Example:

            :~q:foo:bar

        If only two clauses are specified, the flow filter is set to
        match universally (i.e. ".*"). Example:

            /foo/bar

        Clauses are parsed from left to right. Extra separators are taken to be
        part of the final clause. For instance, the last parameter (header-value or
        replace) below is "foo/bar/":

            /one/two/foo/bar/
    """
    sep, rem = option[0], option[1:]
    parts = rem.split(sep, 2)
    if len(parts) == 2:
        flow_filter_pattern = ".*"
        subject, replacement = parts
    elif len(parts) == 3:
        flow_filter_pattern, subject, replacement = parts
    else:
        raise ValueError("Invalid number of parameters (2 or 3 are expected)")

    flow_filter = flowfilter.parse(flow_filter_pattern)
    if not flow_filter:
        raise ValueError(f"Invalid filter pattern: {flow_filter_pattern}")

    subject = strutils.escaped_str_to_bytes(subject)
    replacement = strutils.escaped_str_to_bytes(replacement)

    if replacement.startswith(b"@") and not os.path.isfile(os.path.expanduser(replacement[1:])):
        raise ValueError(f"Invalid file path: {replacement[1:]}")

    return ModifySpec(flow_filter_pattern, flow_filter, subject, replacement)


class ModifyHeaders:
    def __init__(self):
        self.replacements: typing.List[ModifySpec] = []

    def load(self, loader):
        loader.add_option(
            "modify_headers", typing.Sequence[str], [],
            """
            Header modify pattern of the form "[/flow-filter]/header-name/[@]header-value", where the
            separator can be any character. The @ allows to provide a file path that is used to read
            the header value string. An empty header-value removes existing header-name headers.
            """
        )

    def configure(self, updated):
        self.replacements = []
        if "modify_headers" in updated:
            for option in ctx.options.modify_headers:
                try:
                    spec = parse_modify_spec(option)
                except ValueError as e:
                    raise exceptions.OptionsError(
                        f"Cannot parse modify_headers option {option}: {e}"
                    ) from e
                self.replacements.append(spec)

    def run(self, flow, hdrs):
        # unset all specified headers
        for spec in self.replacements:
            if spec.matches(flow):
                hdrs.pop(spec.subject, None)

        # set all specified headers if the replacement string is not empty
        for spec in self.replacements:
            if spec.replacement.startswith(b"@"):
                path = os.path.expanduser(spec.replacement[1:])
                try:
                    with open(path, "rb") as file:
                        replacement = file.read()
                except IOError:
                    ctx.log.warn(f"Could not read replacement file {path}")
                    return
            else:
                replacement = spec.replacement

            if spec.matches(flow) and replacement:
                hdrs.add(spec.subject, replacement)

    def request(self, flow):
        if not flow.reply.has_message:
            self.run(flow, flow.request.headers)

    def response(self, flow):
        if not flow.reply.has_message:
            self.run(flow, flow.response.headers)
