from abc import ABCMeta, abstractmethod

from collections.abc import MutableMapping
from mitmproxy.types import serializable


class _MultiDict(MutableMapping, serializable.Serializable, metaclass=ABCMeta):
    def __repr__(self):
        fields = (
            repr(field)
            for field in self.fields
        )
        return "{cls}[{fields}]".format(
            cls=type(self).__name__,
            fields=", ".join(fields)
        )

    @staticmethod
    @abstractmethod
    def _reduce_values(values):
        """
        If a user accesses multidict["foo"], this method
        reduces all values for "foo" to a single value that is returned.
        For example, HTTP headers are folded, whereas we will just take
        the first cookie we found with that name.
        """

    @staticmethod
    @abstractmethod
    def _kconv(key):
        """
        This method converts a key to its canonical representation.
        For example, HTTP headers are case-insensitive, so this method returns key.lower().
        """

    def __getitem__(self, key):
        values = self.get_all(key)
        if not values:
            raise KeyError(key)
        return self._reduce_values(values)

    def __setitem__(self, key, value):
        self.set_all(key, [value])

    def __delitem__(self, key):
        if key not in self:
            raise KeyError(key)
        key = self._kconv(key)
        self.fields = tuple(
            field for field in self.fields
            if key != self._kconv(field[0])
        )

    def __iter__(self):
        seen = set()
        for key, _ in self.fields:
            key_kconv = self._kconv(key)
            if key_kconv not in seen:
                seen.add(key_kconv)
                yield key

    def __len__(self):
        return len(set(self._kconv(key) for key, _ in self.fields))

    def __eq__(self, other):
        if isinstance(other, MultiDict):
            return self.fields == other.fields
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_all(self, key):
        """
        Return the list of all values for a given key.
        If that key is not in the MultiDict, the return value will be an empty list.
        """
        key = self._kconv(key)
        return [
            value
            for k, value in self.fields
            if self._kconv(k) == key
        ]

    def set_all(self, key, values):
        """
        Remove the old values for a key and add new ones.
        """
        key_kconv = self._kconv(key)

        new_fields = []
        for field in self.fields:
            if self._kconv(field[0]) == key_kconv:
                if values:
                    new_fields.append(
                        (field[0], values.pop(0))
                    )
            else:
                new_fields.append(field)
        while values:
            new_fields.append(
                (key, values.pop(0))
            )
        self.fields = tuple(new_fields)

    def add(self, key, value):
        """
        Add an additional value for the given key at the bottom.
        """
        self.insert(len(self.fields), key, value)

    def insert(self, index, key, value):
        """
        Insert an additional value for the given key at the specified position.
        """
        item = (key, value)
        self.fields = self.fields[:index] + (item,) + self.fields[index:]

    def keys(self, multi=False):
        """
        Get all keys.

        Args:
            multi(bool):
                If True, one key per value will be returned.
                If False, duplicate keys will only be returned once.
        """
        return (
            k
            for k, _ in self.items(multi)
        )

    def values(self, multi=False):
        """
        Get all values.

        Args:
            multi(bool):
                If True, all values will be returned.
                If False, only the first value per key will be returned.
        """
        return (
            v
            for _, v in self.items(multi)
        )

    def items(self, multi=False):
        """
        Get all (key, value) tuples.

        Args:
            multi(bool):
                If True, all (key, value) pairs will be returned
                If False, only the first (key, value) pair per unique key will be returned.
        """
        if multi:
            return self.fields
        else:
            return super().items()

    def collect(self):
        """
            Returns a list of (key, value) tuples, where values are either
            singular if there is only one matching item for a key, or a list
            if there are more than one. The order of the keys matches the order
            in the underlying fields list.
        """
        coll = []
        for key in self:
            values = self.get_all(key)
            if len(values) == 1:
                coll.append([key, values[0]])
            else:
                coll.append([key, values])
        return coll

    def get_state(self):
        return self.fields

    def set_state(self, state):
        self.fields = tuple(tuple(x) for x in state)

    @classmethod
    def from_state(cls, state):
        return cls(state)


class MultiDict(_MultiDict):
    def __init__(self, fields=()):
        super().__init__()
        self.fields = tuple(
            tuple(i) for i in fields
        )

    @staticmethod
    def _reduce_values(values):
        return values[0]

    @staticmethod
    def _kconv(key):
        return key


class MultiDictView(_MultiDict):
    """
    The MultiDictView provides the MultiDict interface over calculated data.
    The view itself contains no state - data is retrieved from the parent on
    request, and stored back to the parent on change.
    """
    def __init__(self, getter, setter):
        self._getter = getter
        self._setter = setter
        super().__init__()

    @staticmethod
    def _kconv(key):
        # All request-attributes are case-sensitive.
        return key

    @staticmethod
    def _reduce_values(values):
        # We just return the first element if
        # multiple elements exist with the same key.
        return values[0]

    @property
    def fields(self):
        return self._getter()

    @fields.setter
    def fields(self, value):
        self._setter(value)
