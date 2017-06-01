from typing import List
import pytest

from mitmproxy.stateobject import StateObject


class Child(StateObject):
    def __init__(self, x):
        self.x = x

    _stateobject_attributes = dict(
        x=int
    )

    @classmethod
    def from_state(cls, state):
        obj = cls(None)
        obj.set_state(state)
        return obj

    def __eq__(self, other):
        return isinstance(other, Child) and self.x == other.x


class Container(StateObject):
    def __init__(self):
        self.child = None
        self.children = None
        self.dictionary = None

    _stateobject_attributes = dict(
        child=Child,
        children=List[Child],
        dictionary=dict,
    )

    @classmethod
    def from_state(cls, state):
        obj = cls()
        obj.set_state(state)
        return obj


def test_simple():
    a = Child(42)
    b = a.copy()
    assert b.get_state() == {"x": 42}
    a.set_state({"x": 44})
    assert a.x == 44
    assert b.x == 42


def test_container():
    a = Container()
    a.child = Child(42)
    b = a.copy()
    assert a.child.x == b.child.x
    b.child.x = 44
    assert a.child.x != b.child.x


def test_container_list():
    a = Container()
    a.children = [Child(42), Child(44)]
    assert a.get_state() == {
        "child": None,
        "children": [{"x": 42}, {"x": 44}],
        "dictionary": None,
    }
    copy = a.copy()
    assert len(copy.children) == 2
    assert copy.children is not a.children
    assert copy.children[0] is not a.children[0]
    assert Container.from_state(a.get_state())


def test_container_dict():
    a = Container()
    a.dictionary = dict()
    a.dictionary['foo'] = 'bar'
    a.dictionary['bar'] = Child(44)
    assert a.get_state() == {
        "child": None,
        "children": None,
        "dictionary": {'bar': {'x': 44}, 'foo': 'bar'},
    }
    copy = a.copy()
    assert len(copy.dictionary) == 2
    assert copy.dictionary is not a.dictionary
    assert copy.dictionary['bar'] is not a.dictionary['bar']


def test_too_much_state():
    a = Container()
    a.child = Child(42)
    s = a.get_state()
    s['foo'] = 'bar'
    b = Container()

    with pytest.raises(RuntimeWarning):
        b.set_state(s)
