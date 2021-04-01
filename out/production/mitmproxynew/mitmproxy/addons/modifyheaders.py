import re
import typing
from pathlib import Path

from mitmproxy import ctx, exceptions, flowfilter, http
from mitmproxy.http import Headers
from mitmproxy.utils import strutils
from mitmproxy.utils.spec import parse_spec


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


def parse_modify_spec(option: str, subject_is_regex: bool) -> ModifySpec:
    flow_filter, subject_str, replacement = parse_spec(option)

    subject = strutils.escaped_str_to_bytes(subject_str)
    if subject_is_regex:
        try:
            re.compile(subject)
        except re.error as e:
            raise ValueError(f"Invalid regular expression {subject!r} ({e})")

    spec = ModifySpec(flow_filter, subject, replacement)

    try:
        spec.read_replacement()
    except OSError as e:
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
        if "modify_headers" in updated:
            self.replacements = []
            for option in ctx.options.modify_headers:
                try:
                    spec = parse_modify_spec(option, False)
                except ValueError as e:
                    raise exceptions.OptionsError(f"Cannot parse modify_headers option {option}: {e}") from e
                self.replacements.append(spec)

    def request(self, flow):
        if flow.response or flow.error or flow.reply.state == "taken":
            return
        self.run(flow, flow.request.headers)

    def response(self, flow):
        if flow.error or flow.reply.state == "taken":
            return
        self.run(flow, flow.response.headers)

    def run(self, flow: http.HTTPFlow, hdrs: Headers) -> None:
        matches = []

        # first check all the filters against the original, unmodified flow
        for spec in self.replacements:
            matches.append(spec.matches(flow))

        # unset all specified headers
        for i, spec in enumerate(self.replacements):
            if matches[i]:
                hdrs.pop(spec.subject, None)

        # set all specified headers if the replacement string is not empty

        for i, spec in enumerate(self.replacements):
            if matches[i]:
                try:
                    replacement = spec.read_replacement()
                except OSError as e:
                    ctx.log.warn(f"Could not read replacement file: {e}")
                    continue
                else:
                    if replacement:
                        hdrs.add(spec.subject, replacement)
