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

    def available_views(self) -> list[str]:
        return ["auto", *sorted(self._by_name.keys())]

    def get_view(
        self, data: bytes, metadata: Metadata, view_name: str = "auto"
    ) -> Contentview:
        """
        Get the best contentview for the given data and metadata.

        If `view_name` is "auto" or the provided view not found,
        the best matching contentview based on `render_priority` will be returned.
        """
        if view_name != "auto":
            try:
                return self[view_name.lower()]
            except KeyError:
                logger.warning(
                    f"Unknown contentview {view_name!r}, selecting best match instead."
                )

        max_prio: tuple[float, Contentview] | None = None
        for name, view in self._by_name.items():
            try:
                priority = view.render_priority(data, metadata)
                assert isinstance(priority, (int, float)), (
                    f"render_priority for {view.name} did not return a number."
                )
            except Exception:
                logger.exception(f"Error in {view.name}.render_priority")
            else:
                if max_prio is None or max_prio[0] < priority:
                    max_prio = (priority, view)
        assert max_prio, "At least one view needs to have a working `render_priority`."
        return max_prio[1]

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._by_name)

    def __getitem__(self, item: str) -> Contentview:
        return self._by_name[item.lower()]

    def __len__(self):
        return len(self._by_name)
