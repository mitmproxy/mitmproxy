import copy
import enum
from dataclasses import dataclass

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
class BuiltinChildren(SerializableDataclass):
    a: list[int] | None
    b: dict[str, int] | None
    c: tuple[int, int] | None
    d: list[Simple]
    e: TEnum | None


@dataclass
class Defaults(SerializableDataclass):
    z: int | None = 42


class TestSerializableDataclass:
    @pytest.mark.parametrize("cls, state", [
        (Simple, {"x": 42, "y": 'foo'}),
        (Simple, {"x": 42, "y": None}),
        (SerializableChild, {"foo": {"x": 42, "y": "foo"}, "maybe_foo": None}),
        (SerializableChild, {"foo": {"x": 42, "y": "foo"}, "maybe_foo": {"x": 42, "y": "foo"}}),
        (Inheritance, {"x": 42, "y": "foo", "z": True}),
        (BuiltinChildren, {"a": [1, 2, 3], "b": {"foo": 42}, "c": (1, 2), "d": [{"x": 42, "y": "foo"}], "e": 1}),
        (BuiltinChildren, {"a": None, "b": None, "c": None, "d": [], "e": None}),
    ])
    def test_roundtrip(self, cls, state):
        a = cls.from_state(copy.deepcopy(state))
        assert a.get_state() == state

    def test_invalid_none(self):
        with pytest.raises(ValueError):
            Simple.from_state({"x": None, "y": "foo"})

    def test_defaults(self):
        a = Defaults.from_state({})
        assert a.get_state() == {"z": 42}

    def test_invalid_type(self):
        with pytest.raises(ValueError):
            Simple.from_state({"x": 42, "y": 42})

    def test_invalid_key(self):
        with pytest.raises(ValueError):
            Simple.from_state({"x": 42, "y": "foo", "z": True})

    def test_invalid_type_in_list(self):
        with pytest.raises(ValueError):
            BuiltinChildren.from_state({"w": [{"x": "foo", "y": "foo"}], "x": None, "y": None, "z": None})
