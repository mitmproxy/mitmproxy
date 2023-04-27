import json
from collections import abc
import typing
from mitmproxy.coretypes import serializable
from mitmproxy.utils import typecheck


class StateObject(serializable.Serializable):
    """
    An object with serializable state.

    State attributes can either be serializable types(str, tuple, bool, ...)
    or StateObject instances themselves.
    """

    _stateobject_attributes: typing.ClassVar[abc.MutableMapping[str, typing.Any]]
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
            raise RuntimeWarning(f"Unexpected State in __setstate__: {state}")


def _process(typeinfo: typecheck.Type, val: typing.Any, make: bool) -> typing.Any:
    if val is None:
        return None
    elif make and hasattr(typeinfo, "from_state"):
        return typeinfo.from_state(val)
    elif not make and hasattr(val, "get_state"):
        return val.get_state()

    origin = typing.get_origin(typeinfo)

    if origin is list:
        T = typing.get_args(typeinfo)[0]
        return [_process(T, x, make) for x in val]
    elif origin is tuple:
        Ts = typing.get_args(typeinfo)
        if len(Ts) != len(val):
            raise ValueError(f"Invalid data. Expected {Ts}, got {val}.")
        return tuple(_process(T, x, make) for T, x in zip(Ts, val))
    elif origin is dict:
        k_cls, v_cls = typing.get_args(typeinfo)
        return {
            _process(k_cls, k, make): _process(v_cls, v, make) for k, v in val.items()
        }
    elif typeinfo is typing.Any:
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
