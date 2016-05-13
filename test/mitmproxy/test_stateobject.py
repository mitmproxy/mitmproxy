from typing import List

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


class Container(StateObject):
    def __init__(self):
        self.child = None
        self.children = None

    _stateobject_attributes = dict(
        child=Child,
        children=List[Child],
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
        "children": [{"x": 42}, {"x": 44}]
    }
    assert len(a.copy().children) == 2
