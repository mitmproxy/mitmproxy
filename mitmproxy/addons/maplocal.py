import re
import typing
import urllib
from pathlib import Path

from mitmproxy import exceptions
from mitmproxy import ctx
from mitmproxy import http
from mitmproxy.addons.modifyheaders import parse_modify_spec, ModifySpec


class MapLocal:
    def __init__(self):
        self.replacements: typing.List[ModifySpec] = []

    def load(self, loader):
        loader.add_option(
            "map_local", typing.Sequence[str], [],
            """
            Replacement pattern of the form "[/flow-filter]/regex/file-or-directory", where
            the separator can be any character. The @ allows to provide a file path that
            is used to read the replacement string.
            """
        )

    def configure(self, updated):
        if "map_local" in updated:
            self.replacements = []
            for option in ctx.options.map_local:
                try:
                    spec = parse_modify_spec(option, True, True)
                except ValueError as e:
                    raise exceptions.OptionsError(f"Cannot parse map_local option {option}: {e}") from e

                self.replacements.append(spec)

    def construct_candidate_path(self, base_path, path_components, filename):
        candidate_path = base_path.joinpath("/".join(path_components + [filename]))
        return str(candidate_path)

    def sanitize_candidate_path(self, candidate_path, base_path):
        try:
            candidate_path.resolve(strict=True)
            if base_path in candidate_path.parents:
                return candidate_path
        except FileNotFoundError:
            pass
        return None

    def file_candidates(self, url: str, spec: ModifySpec) -> typing.List[Path]:
        replacement = spec.replacement_str
        candidates = []

        if replacement.is_file():
            candidates.append(replacement)

        elif replacement.is_dir():
            parsed_url = urllib.parse.urlparse(url)

            path_components = parsed_url.path.lstrip("/").split("/")
            filename = path_components.pop()

            # todo: this can be improved (e.g., also consider index.htm)
            if not filename:
                filename = 'index.html'

            # construct all possible paths
            while True:
                candidates.append(
                    self.construct_candidate_path(replacement, path_components, filename)
                )

                if not path_components:
                    break

                path_components.pop()

        return candidates

    def request(self, flow: http.HTTPFlow) -> None:
        if flow.reply and flow.reply.has_message:
            return
        for spec in self.replacements:
            req = flow.request
            url = req.pretty_url
            base_path = Path(spec.replacement_str)
            if spec.matches(flow) and re.search(spec.subject, url.encode("utf8", "surrogateescape")):
                file_candidates = self.file_candidates(url, spec)
                for file_candidate in file_candidates:
                    file_candidate = Path(file_candidate)
                    if self.sanitize_candidate_path(file_candidate, base_path):
                        try:
                            with open(file_candidate, "rb") as file:
                                replacement = file.read()
                        except IOError:
                            ctx.log.warn(f"Could not read replacement file {file_candidate}")
                            return

                        flow.response = http.HTTPResponse.make( 
                            200,  # (optional) status code
                            replacement,  # (optional) content
                            # todo: guess mime type
                            {"Content-Type": "image/jpeg"}  # (optional) headers
                        )
