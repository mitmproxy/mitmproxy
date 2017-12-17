import copy

from mitmproxy.coretypes import serializable


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
        a = SerializableDummy({
            "id": "foo",
            "foo": 42
        })
        b = a.copy()
        assert a.get_state()["id"] != b.get_state()["id"]
        assert a.get_state()["foo"] == b.get_state()["foo"]
