import typing

import pytest

from mitmproxy.stateobject import StateObject


class TObject(StateObject):
    def __init__(self, x):
        self.x = x

    @classmethod
    def from_state(cls, state):
        obj = cls(None)
        obj.set_state(state)
        return obj


class Child(TObject):
    _stateobject_attributes = dict(
        x=int
    )

    def __eq__(self, other):
        return isinstance(other, Child) and self.x == other.x


class TTuple(TObject):
    _stateobject_attributes = dict(
        x=typing.Tuple[int, Child]
    )


class TList(TObject):
    _stateobject_attributes = dict(
        x=typing.List[Child]
    )


class TDict(TObject):
    _stateobject_attributes = dict(
        x=typing.Dict[str, Child]
    )


class TAny(TObject):
    _stateobject_attributes = dict(
        x=typing.Any
    )


class TSerializableChild(TObject):
    _stateobject_attributes = dict(
        x=Child
    )


def test_simple():
    a = Child(42)
    assert a.get_state() == {"x": 42}
    b = a.copy()
    a.set_state({"x": 44})
    assert a.x == 44
    assert b.x == 42


def test_serializable_child():
    child = Child(42)
    a = TSerializableChild(child)
    assert a.get_state() == {
        "x": {"x": 42}
    }
    a.set_state({
        "x": {"x": 43}
    })
    assert a.x.x == 43
    assert a.x is child
    b = a.copy()
    assert a.x == b.x
    assert a.x is not b.x


def test_tuple():
    a = TTuple((42, Child(43)))
    assert a.get_state() == {
        "x": (42, {"x": 43})
    }
    b = a.copy()
    a.set_state({"x": (44, {"x": 45})})
    assert a.x == (44, Child(45))
    assert b.x == (42, Child(43))


def test_tuple_err():
    a = TTuple(None)
    with pytest.raises(ValueError, match="Invalid data"):
        a.set_state({"x": (42,)})


def test_list():
    a = TList([Child(1), Child(2)])
    assert a.get_state() == {
        "x": [{"x": 1}, {"x": 2}],
    }
    copy = a.copy()
    assert len(copy.x) == 2
    assert copy.x is not a.x
    assert copy.x[0] is not a.x[0]


def test_dict():
    a = TDict({"foo": Child(42)})
    assert a.get_state() == {
        "x": {"foo": {"x": 42}}
    }
    b = a.copy()
    assert list(a.x.items()) == list(b.x.items())
    assert a.x is not b.x
    assert a.x["foo"] is not b.x["foo"]


def test_any():
    a = TAny(42)
    b = a.copy()
    assert a.x == b.x

    a = TAny(object())
    with pytest.raises(ValueError):
        a.get_state()


def test_too_much_state():
    a = Child(42)
    s = a.get_state()
    s['foo'] = 'bar'

    with pytest.raises(RuntimeWarning):
        a.set_state(s)


def test_none():
    a = Child(None)
    assert a.get_state() == {"x": None}
    a = Child(42)
    a.set_state({"x": None})
    assert a.x is None
