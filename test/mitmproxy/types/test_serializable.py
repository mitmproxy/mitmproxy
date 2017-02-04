from mitmproxy.types import serializable


class SerializableDummy(serializable.Serializable):
    def __init__(self, i):
        self.i = i

    def get_state(self):
        return self.i

    def set_state(self, i):
        self.i = i

    def from_state(self, state):
        return type(self)(state)


class TestSerializable:

    def test_copy(self):
        a = SerializableDummy(42)
        assert a.i == 42
        b = a.copy()
        assert b.i == 42

        a.set_state(1)
        assert a.i == 1
        assert b.i == 42
