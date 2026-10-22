import io

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata


class YAMLContentview(Contentview):
    syntax_highlight = "yaml"

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        text = data.decode("utf-8", "surrogateescape")
        if not text.strip():
            return ""
        yaml_parser = YAML(typ="rt", pure=True)
        try:
            docs = list(yaml_parser.load_all(text))
        except YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}") from e
    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        if not data or not metadata.content_type:
            return 0
        ct = metadata.content_type
        if ct.startswith(("application/", "text/")) and (
            ct.endswith("yaml") or ct.endswith("yml")
        ):
            return 1
        return 0


yaml = YAMLContentview()
