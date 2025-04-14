from ._api import Contentview
from ._api import Metadata


class RawContentview(Contentview):
    def prettify(self, data: bytes, metadata: Metadata) -> str:
        return data.decode("utf-8", "backslashreplace")

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        return 0.1


raw = RawContentview()
