from __future__ import annotations

import logging
import typing
from collections.abc import Mapping

from ..utils import signals
from ._api import Contentview
from ._api import Metadata

logger = logging.getLogger(__name__)


def _on_change(view: Contentview) -> None: ...


class ContentviewRegistry(Mapping[str, Contentview]):
    def __init__(self):
        self._by_name: dict[str, Contentview] = {}
        self.on_change = signals.SyncSignal(_on_change)

    def register(self, instance: Contentview | type[Contentview]) -> None:
        if isinstance(instance, type):
            instance = instance()
        name = instance.name.lower()
        if name in self._by_name:
            logger.info(f"Replacing existing {name} contentview.")
        self._by_name[name] = instance
        self.on_change.send(instance)

    def get_view(
        self, data: bytes, metadata: Metadata, view_name: str | None
    ) -> Contentview:
        """
        Get the best contentview for the given data and metadata.

        If the provided view_name is not found, we fall back gracefully to using `render_priority`.
        """
        if view_name:
            try:
                return self[view_name.lower()]
            except KeyError:
                logger.warning(
                    f"Unknown contentview {view_name!r}, selecting best match instead."
                )

        return max(self.values(), key=lambda cv: cv.render_priority(data, metadata))

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._by_name)

    def __getitem__(self, item: str) -> Contentview:
        return self._by_name[item.lower()]

    def __len__(self):
        return len(self._by_name)
