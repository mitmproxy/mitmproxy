import re
import typing
from pathlib import Path

from mitmproxy import exceptions, http
from mitmproxy import flowfilter
from mitmproxy.net.http import Headers
from mitmproxy.utils import strutils
from mitmproxy import ctx


class ModifySpec(typing.NamedTuple):
    matches: flowfilter.TFilter
    subject: bytes
    replacement_str: str

    def read_replacement(self) -> bytes:
        """
        Process the replacement str. This usually just involves converting it to bytes.
        However, if it starts with `@`, we interpret the rest as a file path to read from.

        Raises:
            - IOError if the file cannot be read.
        """
        if self.replacement_str.startswith("@"):
            return Path(self.replacement_str[1:]).expanduser().read_bytes()
        else:
            # We could cache this at some point, but unlikely to be a problem.
            return strutils.escaped_str_to_bytes(self.replacement_str)


def _match_all(flow) -> bool:
    return True


def parse_modify_spec(option, subject_is_regex: bool) -> ModifySpec:
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
        flow_filter = _match_all
        subject, replacement = parts
    elif len(parts) == 3:
        flow_filter_pattern, subject, replacement = parts
        flow_filter = flowfilter.parse(flow_filter_pattern)  # type: ignore
        if not flow_filter:
            raise ValueError(f"Invalid filter pattern: {flow_filter_pattern}")
    else:
        raise ValueError("Invalid number of parameters (2 or 3 are expected)")

    subject = strutils.escaped_str_to_bytes(subject)
    if subject_is_regex:
        try:
            re.compile(subject)
        except re.error as e:
            raise ValueError(f"Invalid regular expression {subject!r} ({e})")

    spec = ModifySpec(flow_filter, subject, replacement)

    try:
        spec.read_replacement()
    except IOError as e:
        raise ValueError(f"Invalid file path: {replacement[1:]} ({e})")

    return spec


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
                    spec = parse_modify_spec(option, False)
                except ValueError as e:
                    raise exceptions.OptionsError(f"Cannot parse modify_headers option {option}: {e}") from e
                self.replacements.append(spec)

    def request(self, flow):
        if not flow.reply.has_message:
            self.run(flow, flow.request.headers)

    def response(self, flow):
        if not flow.reply.has_message:
            self.run(flow, flow.response.headers)

    def run(self, flow: http.HTTPFlow, hdrs: Headers) -> None:
        # unset all specified headers
        for spec in self.replacements:
            if spec.matches(flow):
                hdrs.pop(spec.subject, None)

        # set all specified headers if the replacement string is not empty
        for spec in self.replacements:
            if spec.matches(flow):
                try:
                    replacement = spec.read_replacement()
                except IOError as e:
                    ctx.log.warn(f"Could not read replacement file: {e}")
                    continue
                else:
                    if replacement:
                        hdrs.add(spec.subject, replacement)
