from __future__ import absolute_import


class StateObject(object):
    """
        An object with serializable state.

        State attributes can either be serializable types(str, tuple, bool, ...)
        or StateObject instances themselves.
    """
    # An attribute-name -> class-or-type dict containing all attributes that
    # should be serialized. If the attribute is a class, it must implement the
    # StateObject protocol.
    _stateobject_attributes = None
    # A set() of attributes that should be ignored for short state
    _stateobject_long_attributes = frozenset([])

    def from_state(self, state):
        raise NotImplementedError()

    def get_state(self, short=False):
        """
            Retrieve object state. If short is true, return an abbreviated
            format with long data elided.
        """
        state = {}
        for attr, cls in self._stateobject_attributes.iteritems():
            if short and attr in self._stateobject_long_attributes:
                continue
            val = getattr(self, attr)
            if hasattr(val, "get_state"):
                state[attr] = val.get_state(short)
            else:
                state[attr] = val
        return state

    def load_state(self, state):
        """
            Load object state from data returned by a get_state call.
        """
        for attr, cls in self._stateobject_attributes.iteritems():
            if state.get(attr, None) is None:
                setattr(self, attr, None)
            else:
                curr = getattr(self, attr)
                if hasattr(curr, "load_state"):
                    curr.load_state(state[attr])
                elif hasattr(cls, "from_state"):
                    setattr(self, attr, cls.from_state(state[attr]))
                else:
                    setattr(self, attr, cls(state[attr]))
