import mimetypes
import re
import typing
import urllib
from pathlib import Path
from werkzeug.security import safe_join

from mitmproxy import ctx, exceptions, http
from mitmproxy.addons.modifyheaders import parse_modify_spec, ModifySpec


def get_mime_type(file_path: str) -> str:
    mimetype = (
        mimetypes.guess_type(file_path)[0]
        or "application/octet-stream"
    )
    return mimetype


def file_candidates(url: str, base_path: str) -> typing.List[Path]:
    candidates = []
    parsed_url = urllib.parse.urlparse(url)
    path_components = parsed_url.path.lstrip("/").split("/")
    filename = path_components.pop()

    # todo: we may want to consider other filenames such as index.htm)
    if not filename:
        filename = 'index.html'

    # construct all possible paths
    while True:
        components_with_filename = tuple(path_components + [filename])
        candidate_path = safe_join(base_path, *components_with_filename)
        if candidate_path:
            candidates.append(
                Path(candidate_path)
            )

        if not path_components:
            break

        path_components.pop()

    return candidates


class MapLocal:
    def __init__(self):
        self.replacements: typing.List[ModifySpec] = []

    def load(self, loader):
        loader.add_option(
            "map_local", typing.Sequence[str], [],
            """
            Map remote resources to a local file using a pattern of the form
            "[/flow-filter]/url-regex/file-or-directory-path", where the
            separator can be any character.
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

    def request(self, flow: http.HTTPFlow) -> None:
        if flow.reply and flow.reply.has_message:
            return

        for spec in self.replacements:
            req = flow.request
            url = req.pretty_url
            base_path = Path(spec.replacement)

            if spec.matches(flow) and re.search(spec.subject, url.encode("utf8", "surrogateescape")):
                replacement_path = None
                if base_path.is_file():
                    replacement_path = base_path
                elif base_path.is_dir():
                    candidates = file_candidates(url, str(base_path))
                    for candidate in candidates:
                        # check that path is not outside of the user-defined base_path
                        if candidate.is_file() and base_path in candidate.parents:
                            replacement_path = candidate
                            break

                if replacement_path:
                    try:
                        flow.response = http.HTTPResponse.make(
                            200,
                            replacement_path.read_bytes(),
                            {"Content-Type": get_mime_type(str(replacement_path))}
                        )
                        # only set flow.response once, for the first matching rule
                        break
                    except IOError:
                        ctx.log.warn(f"Could not read replacement file {replacement_path}")
                        return
