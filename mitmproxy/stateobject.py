from __future__ import absolute_import

import six
from typing import List, Any

from netlib.utils import Serializable


def _is_list(cls):
    # The typing module backport is somewhat broken.
    # Python 3.5 or 3.6 should fix this.
    is_list_bugfix = getattr(cls, "__origin__", False) == getattr(List[Any], "__origin__", True)
    return issubclass(cls, List) or is_list_bugfix


class StateObject(Serializable):

    """
    An object with serializable state.

    State attributes can either be serializable types(str, tuple, bool, ...)
    or StateObject instances themselves.
    """

    _stateobject_attributes = None
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
        for attr, cls in six.iteritems(self._stateobject_attributes):
            val = getattr(self, attr)
            if val is None:
                state[attr] = None
            elif hasattr(val, "get_state"):
                state[attr] = val.get_state()
            elif _is_list(cls):
                state[attr] = [x.get_state() for x in val]
            else:
                state[attr] = val
        return state

    def set_state(self, state):
        """
        Load object state from data returned by a get_state call.
        """
        state = state.copy()
        for attr, cls in six.iteritems(self._stateobject_attributes):
            if state.get(attr) is None:
                setattr(self, attr, state.pop(attr))
            else:
                curr = getattr(self, attr)
                if hasattr(curr, "set_state"):
                    curr.set_state(state.pop(attr))
                elif hasattr(cls, "from_state"):
                    obj = cls.from_state(state.pop(attr))
                    setattr(self, attr, obj)
                elif _is_list(cls):
                    cls = cls.__parameters__[0]
                    setattr(self, attr, [cls.from_state(x) for x in state.pop(attr)])
                else:  # primitive types such as int, str, ...
                    setattr(self, attr, cls(state.pop(attr)))
        if state:
            raise RuntimeWarning("Unexpected State in __setstate__: {}".format(state))
