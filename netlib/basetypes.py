import six
import abc


@six.add_metaclass(abc.ABCMeta)
class Serializable(object):
    """
    Abstract Base Class that defines an API to save an object's state and restore it later on.
    """

    @classmethod
    @abc.abstractmethod
    def from_state(cls, state):
        """
        Create a new object from the given state.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_state(self):
        """
        Retrieve object state.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def set_state(self, state):
        """
        Set object state to the given state.
        """
        raise NotImplementedError()

    def copy(self):
        return self.from_state(self.get_state())
