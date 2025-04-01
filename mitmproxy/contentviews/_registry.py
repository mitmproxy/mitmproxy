from __future__ import annotations

import logging
import typing
from collections.abc import Iterable, Mapping

from ..utils import signals

if typing.TYPE_CHECKING:
    from ._api import Contentview


logger = logging.getLogger(__name__)


def _on_change(view: Contentview) -> None: ...


class ContentviewRegistry(Mapping[str, Contentview]):
    def __init__(self):
        self._by_name: dict[str, Contentview] = {}
        self.on_change = signals.SyncSignal(_on_change)

    def register(self, instance: Contentview) -> None:
        name = instance.name.lower()
        if name in self._by_name:
            logger.info(f"Replacing existing {name} contentview.")
        self._by_name[name] = instance
        self.on_change.send(instance)

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._by_name)

    def __getitem__(self, item: str) -> Contentview:
        return self._by_name[item.lower()]

    def __len__(self):
        return len(self._by_name)
