from __future__ import annotations

import copy
import dataclasses
import enum
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

import pytest

from mitmproxy.coretypes import serializable
from mitmproxy.coretypes.serializable import SerializableDataclass


class SerializableDummy(serializable.Serializable):
    def __init__(self, i):
        self.i = i

    def get_state(self):
        return copy.copy(self.i)

    def set_state(self, i):
        self.i = i

    @classmethod
    def from_state(cls, state):
        return cls(state)


class TestSerializable:
    def test_copy(self):
        a = SerializableDummy(42)
        assert a.i == 42
        b = a.copy()
        assert b.i == 42

        a.set_state(1)
        assert a.i == 1
        assert b.i == 42

    def test_copy_id(self):
        a = SerializableDummy({"id": "foo", "foo": 42})
        b = a.copy()
        assert a.get_state()["id"] != b.get_state()["id"]
        assert a.get_state()["foo"] == b.get_state()["foo"]


@dataclass
class Simple(SerializableDataclass):
    x: int
    y: str | None


@dataclass
class SerializableChild(SerializableDataclass):
    foo: Simple
    maybe_foo: Simple | None


@dataclass
class Inheritance(Simple):
    z: bool


class TEnum(enum.Enum):
    A = 1
    B = 2


@dataclass
class TLiteral(SerializableDataclass):
    lit: Literal["foo", "bar"]


@dataclass
class BuiltinChildren(SerializableDataclass):
    a: list[int] | None
    b: dict[str, int] | None
    c: tuple[int, int] | None
    d: list[Simple]
    e: TEnum | None


@dataclass
class Defaults(SerializableDataclass):
    z: int | None = 42


@dataclass
class Unsupported(SerializableDataclass):
    a: Mapping[str, int]


@dataclass
class Addr(SerializableDataclass):
    peername: tuple[str, int]


@dataclass(frozen=True)
class Frozen(SerializableDataclass):
    x: int


@dataclass
class FrozenWrapper(SerializableDataclass):
    f: Frozen


class TestSerializableDataclass:
    @pytest.mark.parametrize(
        "cls, state",
        [
            (Simple, {"x": 42, "y": "foo"}),
            (Simple, {"x": 42, "y": None}),
            (SerializableChild, {"foo": {"x": 42, "y": "foo"}, "maybe_foo": None}),
            (
                SerializableChild,
                {"foo": {"x": 42, "y": "foo"}, "maybe_foo": {"x": 42, "y": "foo"}},
            ),
            (Inheritance, {"x": 42, "y": "foo", "z": True}),
            (
                BuiltinChildren,
                {
                    "a": [1, 2, 3],
                    "b": {"foo": 42},
                    "c": (1, 2),
                    "d": [{"x": 42, "y": "foo"}],
                    "e": 1,
                },
            ),
            (BuiltinChildren, {"a": None, "b": None, "c": None, "d": [], "e": None}),
            (TLiteral, {"lit": "foo"}),
        ],
    )
    def test_roundtrip(self, cls, state):
        a = cls.from_state(copy.deepcopy(state))
        assert a.get_state() == state

    def test_set(self):
        s = SerializableChild(foo=Simple(x=42, y=None), maybe_foo=Simple(x=43, y=None))
        s.set_state({"foo": {"x": 44, "y": None}, "maybe_foo": None})
        assert s.foo.x == 44
        assert s.maybe_foo is None
        with pytest.raises(ValueError, match="Unexpected fields"):
            Simple(0, "").set_state({"x": 42, "y": "foo", "z": True})

    def test_invalid_none(self):
        with pytest.raises(ValueError):
            Simple.from_state({"x": None, "y": "foo"})

    def test_defaults(self):
        a = Defaults()
        assert a.get_state() == {"z": 42}

    def test_invalid_type(self):
        with pytest.raises(ValueError):
            Simple.from_state({"x": 42, "y": 42})
        with pytest.raises(ValueError):
            BuiltinChildren.from_state(
                {"a": None, "b": None, "c": ("foo",), "d": [], "e": None}
            )

    def test_invalid_key(self):
        with pytest.raises(ValueError):
            Simple.from_state({"x": 42, "y": "foo", "z": True})

    def test_invalid_type_in_list(self):
        with pytest.raises(ValueError, match="Invalid value for x"):
            BuiltinChildren.from_state(
                {
                    "a": None,
                    "b": None,
                    "c": None,
                    "d": [{"x": "foo", "y": "foo"}],
                    "e": None,
                }
            )

    def test_unsupported_type(self):
        with pytest.raises(TypeError):
            Unsupported.from_state({"a": "foo"})

    def test_literal(self):
        assert TLiteral.from_state({"lit": "foo"}).get_state() == {"lit": "foo"}
        with pytest.raises(ValueError):
            TLiteral.from_state({"lit": "unknown"})

    def test_peername(self):
        assert Addr.from_state({"peername": ("addr", 42)}).get_state() == {
            "peername": ("addr", 42)
        }
        assert Addr.from_state({"peername": ("addr", 42, 0, 0)}).get_state() == {
            "peername": ("addr", 42, 0, 0)
        }

    def test_set_immutable(self):
        w = FrozenWrapper(Frozen(42))
        with pytest.raises(dataclasses.FrozenInstanceError):
            w.f.set_state({"x": 43})
        w.set_state({"f": {"x": 43}})
        assert w.f.x == 43
