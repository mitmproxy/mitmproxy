"""Regression fixture for #8279.

A script that defines a ``@dataclass``. dataclasses looks the defining module
up in ``sys.modules`` by its ``__module__`` name while the class body runs, so
loading this script fails unless ``load_script`` registers the module in
``sys.modules`` before executing it. The ``ClassVar`` field combined with
deferred annotations forces dataclasses down the string-based type-resolution
path that performs the lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class C:
    x: int
    counter: ClassVar[int] = 0


addons = [C(1)]
