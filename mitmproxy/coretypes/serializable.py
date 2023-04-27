import abc
import uuid
from typing import TypeVar

T = TypeVar("T", bound="Serializable")


class Serializable(metaclass=abc.ABCMeta):
    """
    Abstract Base Class that defines an API to save an object's state and restore it later on.
    """

    @classmethod
    @abc.abstractmethod
    def from_state(cls: type[T], state) -> T:
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

    def copy(self: T) -> T:
        state = self.get_state()
        if isinstance(state, dict) and "id" in state:
            state["id"] = str(uuid.uuid4())
        return self.from_state(state)
