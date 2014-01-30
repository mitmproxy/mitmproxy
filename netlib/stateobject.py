from types import ClassType


class StateObject:
    def _get_state(self):
        raise NotImplementedError

    def _load_state(self, state):
        raise NotImplementedError

    @classmethod
    def _from_state(cls, state):
        raise NotImplementedError

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
        return {attr: self.__get_state_attr(attr, cls)
                for attr, cls in self._stateobject_attributes.iteritems()}

    def __get_state_attr(self, attr, cls):
        """
        helper for _get_state.
        returns the value of the given attribute
        """
        if getattr(self, attr) is None:
            return None
        if isinstance(cls, ClassType):
            return getattr(self, attr)._get_state()
        else:
            return getattr(self, attr)

    def _load_state(self, state):
        for attr, cls in self._stateobject_attributes.iteritems():
            self.__load_state_attr(attr, cls, state)

    def __load_state_attr(self, attr, cls, state):
        """
        helper for _load_state.
        loads the given attribute from the state.
        """
        if state[attr] is not None:  # First, catch None as value.
            if isinstance(cls, ClassType):  # Is the attribute a StateObject itself?
                assert issubclass(cls, StateObject)
                curr = getattr(self, attr)
                if curr:  # if the attribute is already present, delegate to the objects ._load_state method.
                    curr._load_state(state[attr])
                else: # otherwise, create a new object.
                    setattr(self, attr, cls._from_state(state[attr]))
            else:
                setattr(self, attr, cls(state[attr]))
        else:
            setattr(self, attr, None)

    @classmethod
    def _from_state(cls, state):
        f = cls()  # the default implementation assumes an empty constructor. Override accordingly.
        f._load_state(state)
        return f