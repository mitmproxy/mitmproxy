from __future__ import absolute_import, print_function, division

from abc import ABCMeta, abstractmethod

from typing import Tuple

try:
    from collections.abc import MutableMapping
except ImportError:  # pragma: no cover
    from collections import MutableMapping  # Workaround for Python < 3.3

import six

from .utils import Serializable


@six.add_metaclass(ABCMeta)
class MultiDict(MutableMapping, Serializable):
    def __init__(self, fields=None):

        # it is important for us that .fields is immutable, so that we can easily
        # detect changes to it.
        self.fields = tuple(fields) if fields else tuple()  # type: Tuple[Tuple[bytes, bytes], ...]

        for key, value in self.fields:
            if not isinstance(key, bytes) or not isinstance(value, bytes):
                raise TypeError("MultiDict fields must be bytes.")

    def __repr__(self):
        fields = tuple(
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
        pass

    @staticmethod
    @abstractmethod
    def _kconv(v):
        pass

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
        Return the list of items for a given key.
        If that key is not in the MultiDict,
        the return value will be an empty list.
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
                        (key, values.pop(0))
                    )
            else:
                new_fields.append(field)
        while values:
            new_fields.append(
                (key, values.pop(0))
            )
        self.fields = tuple(new_fields)

    def add(self, key, value):
        self.insert(len(self.fields), key, value)

    def insert(self, index, key, value):
        item = (key, value)
        self.fields = self.fields[:index] + (item,) + self.fields[index:]

    def keys(self, multi=False):
        return (
            k
            for k, _ in self.items(multi)
        )

    def values(self, multi=False):
        return (
            v
            for _, v in self.items(multi)
        )

    def items(self, multi=False):
        if multi:
            return self.fields
        else:
            return super(MultiDict, self).items()

    def to_dict(self):
        d = {}
        for key in self:
            values = self.get_all(key)
            if len(values) == 1:
                d[key] = values[0]
            else:
                d[key] = values
        return d

    def get_state(self):
        return self.fields

    def set_state(self, state):
        self.fields = tuple(tuple(x) for x in state)

    @classmethod
    def from_state(cls, state):
        return cls(tuple(x) for x in state)
