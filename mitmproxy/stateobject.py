import json
import typing

from mitmproxy.coretypes import serializable
from mitmproxy.utils import typecheck


class StateObject(serializable.Serializable):
    """
    An object with serializable state.

    State attributes can either be serializable types(str, tuple, bool, ...)
    or StateObject instances themselves.
    """

    _stateobject_attributes: typing.ClassVar[typing.MutableMapping[str, typing.Any]]
    """
    An attribute-name -> class-or-type dict containing all attributes that
    should be serialized. If the attribute is a class, it must implement the
    Serializable protocol.
    """

    def get_state(self):
        """
        Retrieve object state.
        """
        state = {}
        for attr, cls in self._stateobject_attributes.items():
            val = getattr(self, attr)
            state[attr] = get_state(cls, val)
        return state

    def set_state(self, state):
        """
        Load object state from data returned by a get_state call.
        """
        state = state.copy()
        for attr, cls in self._stateobject_attributes.items():
            val = state.pop(attr)
            if val is None:
                setattr(self, attr, val)
            else:
                curr = getattr(self, attr, None)
                if hasattr(curr, "set_state"):
                    curr.set_state(val)
                else:
                    setattr(self, attr, make_object(cls, val))
        if state:
            raise RuntimeWarning("Unexpected State in __setstate__: {}".format(state))


def _process(typeinfo: typecheck.Type, val: typing.Any, make: bool) -> typing.Any:
    if val is None:
        return None
    elif make and hasattr(typeinfo, "from_state"):
        return typeinfo.from_state(val)
    elif not make and hasattr(val, "get_state"):
        return val.get_state()

    typename = str(typeinfo)

    if typename.startswith("typing.List"):
        T = typecheck.sequence_type(typeinfo)
        return [_process(T, x, make) for x in val]
    elif typename.startswith("typing.Tuple"):
        Ts = typecheck.tuple_types(typeinfo)
        if len(Ts) != len(val):
            raise ValueError("Invalid data. Expected {}, got {}.".format(Ts, val))
        return tuple(
            _process(T, x, make) for T, x in zip(Ts, val)
        )
    elif typename.startswith("typing.Dict"):
        k_cls, v_cls = typecheck.mapping_types(typeinfo)
        return {
            _process(k_cls, k, make): _process(v_cls, v, make)
            for k, v in val.items()
        }
    elif typename.startswith("typing.Any"):
        # This requires a bit of explanation. We can't import our IO layer here,
        # because it causes a circular import. Rather than restructuring the
        # code for this, we use JSON serialization, which has similar primitive
        # type restrictions as tnetstring, to check for conformance.
        try:
            json.dumps(val)
        except TypeError:
            raise ValueError(f"Data not serializable: {val}")
        return val
    else:
        return typeinfo(val)


def make_object(typeinfo: typecheck.Type, val: typing.Any) -> typing.Any:
    """Create an object based on the state given in val."""
    return _process(typeinfo, val, True)


def get_state(typeinfo: typecheck.Type, val: typing.Any) -> typing.Any:
    """Get the state of the object given as val."""
    return _process(typeinfo, val, False)
