from __future__ import absolute_import

import six

from netlib.utils import Serializable


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
            if hasattr(val, "get_state"):
                state[attr] = val.get_state()
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
                else:  # primitive types such as int, str, ...
                    setattr(self, attr, cls(state.pop(attr)))
        if state:
            raise RuntimeWarning("Unexpected State in __setstate__: {}".format(state))
