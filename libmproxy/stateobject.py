from __future__ import absolute_import


class StateObject(object):
    """
        An object with serializable state.

        State attributes can either be serializable types(str, tuple, bool, ...)
        or StateObject instances themselves.
    """
    # An attribute-name -> class-or-type dict containing all attributes that
    # should be serialized. If the attribute is a class, it must be a subclass
    # of StateObject.
    _stateobject_attributes = None

    def _get_state_attr(self, attr, cls):
        val = getattr(self, attr)
        if hasattr(val, "get_state"):
            return val.get_state()
        else:
            return val

    def from_state(self):
        raise NotImplementedError

    def get_state(self):
        state = {}
        for attr, cls in self._stateobject_attributes.iteritems():
            state[attr] = self._get_state_attr(attr, cls)
        return state

    def load_state(self, state):
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
