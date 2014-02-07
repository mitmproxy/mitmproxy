class StateObject(object):
    def _get_state(self):
        raise NotImplementedError  # pragma: nocover

    def _load_state(self, state):
        raise NotImplementedError  # pragma: nocover

    @classmethod
    def _from_state(cls, state):
        raise NotImplementedError  # pragma: nocover
        # Usually, this function roughly equals to the following code:
        # f = cls()
        # f._load_state(state)
        # return f

    def __eq__(self, other):
        try:
            return self._get_state() == other._get_state()
        except AttributeError:  # we may compare with something that's not a StateObject
            return False


class SimpleStateObject(StateObject):
    """
    A StateObject with opionated conventions that tries to keep everything DRY.

    Simply put, you agree on a list of attributes and their type.
    Attributes can either be primitive types(str, tuple, bool, ...) or StateObject instances themselves.
    SimpleStateObject uses this information for the default _get_state(), _from_state(s) and _load_state(s) methods.
    Overriding _get_state or _load_state to add custom adjustments is always possible.
    """

    _stateobject_attributes = None  # none by default to raise an exception if definition was forgotten
    """
    An attribute-name -> class-or-type dict containing all attributes that should be serialized
    If the attribute is a class, this class must be a subclass of StateObject.
    """

    def _get_state(self):
        return {attr: self._get_state_attr(attr, cls)
                for attr, cls in self._stateobject_attributes.iteritems()}

    def _get_state_attr(self, attr, cls):
        """
        helper for _get_state.
        returns the value of the given attribute
        """
        val = getattr(self, attr)
        if hasattr(val, "_get_state"):
            return val._get_state()
        else:
            return val

    def _load_state(self, state):
        for attr, cls in self._stateobject_attributes.iteritems():
            self._load_state_attr(attr, cls, state)

    def _load_state_attr(self, attr, cls, state):
        """
        helper for _load_state.
        loads the given attribute from the state.
        """
        if state.get(attr, None) is None:
            setattr(self, attr, None)
            return

        curr = getattr(self, attr)
        if hasattr(curr, "_load_state"):
            curr._load_state(state[attr])
        elif hasattr(cls, "_from_state"):
            setattr(self, attr, cls._from_state(state[attr]))
        else:
            setattr(self, attr, cls(state[attr]))