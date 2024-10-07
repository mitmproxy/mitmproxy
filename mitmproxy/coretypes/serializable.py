# SPDX-License-Identifier: BSD-3-Clause

"""
Improved implementation of a Serializable abstract base class with dataclass support.
Includes enhanced error handling, consistent formatting, and modularization.
"""

import abc
import collections.abc
import dataclasses
import enum
import typing
import uuid
from functools import cache
from typing import TypeVar, Any, Optional, Union, Tuple

try:
    from types import NoneType, UnionType
except ImportError:  # pragma: no cover
    class UnionType:  # type: ignore
        pass
    NoneType = type(None)  # type: ignore

T = TypeVar("T", bound="Serializable")
U = TypeVar("U", bound="SerializableDataclass")
State = Any


class Serializable(metaclass=abc.ABCMeta):
    """
    Abstract Base Class that defines an API to save an object's state and restore it later on.
    """

    @classmethod
    @abc.abstractmethod
    def from_state(cls: type[T], state: State) -> T:
        """
        Create a new object from the given state.
        Consumes the passed state.
        """
        print(f"[DEBUG] Creating object from state: {state}")
        raise NotImplementedError()

    @abc.abstractmethod
    def get_state(self) -> State:
        """
        Retrieve object state.
        """
        print(f"[DEBUG] Retrieving state of object: {self}")
        raise NotImplementedError()

    @abc.abstractmethod
    def set_state(self, state: State) -> None:
        """
        Set object state to the given state. Consumes the passed state.
        May return a `dataclasses.FrozenInstanceError` if the object is immutable.
        """
        print(f"[DEBUG] Setting state of object: {self} with state: {state}")
        raise NotImplementedError()

    def copy(self: T) -> T:
        """
        Create a copy of the current object, assigning a new unique ID if applicable.
        """
        print(f"[DEBUG] Creating copy of object: {self}")
        state = self.get_state()
        if isinstance(state, dict) and "id" in state:
            state["id"] = str(uuid.uuid4())
            print(f"[DEBUG] Assigned new unique ID: {state['id']}")
        return self.from_state(state)


class SerializableDataclass(Serializable):
    """
    A Serializable implementation for dataclasses.
    """

    @classmethod
    @cache
    def __fields(cls) -> Tuple[dataclasses.Field, ...]:
        """
        Cache and return the fields of the dataclass that are serializable.
        """
        print(f"[DEBUG] Retrieving serializable fields for dataclass: {cls.__name__}")
        hints = typing.get_type_hints(cls)
        fields = []
        for field in dataclasses.fields(cls):
            if field.metadata.get("serialize", True) is False:
                continue
            if isinstance(field.type, str):
                field.type = hints[field.name]
            fields.append(field)
        return tuple(fields)

    def get_state(self) -> State:
        """
        Retrieve the state of the dataclass as a dictionary.
        """
        print(f"[DEBUG] Retrieving state for dataclass: {self}")
        state = {}
        for field in self.__fields():
            val = getattr(self, field.name)
            state[field.name] = _to_state(val, field.type, field.name)
            print(f"[DEBUG] Retrieved field '{field.name}' with value: {val}")
        return state

    @classmethod
    def from_state(cls: type[U], state: State) -> U:
        """
        Create a new instance of the dataclass from the given state.
        """
        print(f"[DEBUG] Creating dataclass instance from state: {state}")
        for field in cls.__fields():
            state[field.name] = _to_val(state[field.name], field.type, field.name)
            print(f"[DEBUG] Processed field '{field.name}' with value: {state[field.name]}")
        try:
            return cls(**state)  # type: ignore
        except TypeError as e:
            print(f"[ERROR] Invalid state for {cls}: {e} ({state=})")
            raise ValueError(f"Invalid state for {cls}: {e} ({state=})") from e

    def set_state(self, state: State) -> None:
        """
        Set the current object's state to the provided state.
        """
        print(f"[DEBUG] Setting state for dataclass: {self} with state: {state}")
        for field in self.__fields():
            current = getattr(self, field.name)
            f_state = state.pop(field.name)
            print(f"[DEBUG] Setting field '{field.name}' from state: {f_state}")
            if isinstance(current, Serializable) and f_state is not None:
                try:
                    current.set_state(f_state)
                    continue
                except dataclasses.FrozenInstanceError:
                    pass
            val = _to_val(f_state, field.type, field.name)
            try:
                setattr(self, field.name, val)
            except dataclasses.FrozenInstanceError:
                state[field.name] = f_state  # Restore state dict.
                print(f"[ERROR] Cannot set field '{field.name}' due to FrozenInstanceError")
                raise

        if state:
            print(f"[ERROR] Unexpected fields in {type(self).__name__}.set_state: {state}")
            raise ValueError(
                f"Unexpected fields in {type(self).__name__}.set_state: {state}"
            )


V = TypeVar("V")


def _process(attr_val: Any, attr_type: type[V], attr_name: str, make: bool) -> V:
    """
    Process an attribute value for serialization or deserialization.

    Args:
        attr_val: The value to be processed.
        attr_type: The expected type of the attribute.
        attr_name: The name of the attribute.
        make: Whether to create an object from the state (`True`) or get the state (`False`).

    Returns:
        The processed attribute value.
    """
    print(f"[DEBUG] Processing attribute '{attr_name}' with value: {attr_val} and type: {attr_type}")
    origin = typing.get_origin(attr_type)
    if origin is typing.Literal:
        if attr_val not in typing.get_args(attr_type):
            print(f"[ERROR] Invalid value for {attr_name}: {attr_val!r}")
            raise ValueError(
                f"Invalid value for {attr_name}: {attr_val!r} does not match any literal value."
            )
        return attr_val

    if origin in (UnionType, typing.Union):
        attr_type, nt = typing.get_args(attr_type)
        assert nt is NoneType, f"{attr_name}: only `x | None` union types are supported."
        if attr_val is None:
            return None  # type: ignore
        return _process(attr_val, attr_type, attr_name, make)

    if attr_val is None:
        print(f"[ERROR] Attribute {attr_name} must not be None.")
        raise ValueError(f"Attribute {attr_name} must not be None.")

    if make and hasattr(attr_type, "from_state"):
        print(f"[DEBUG] Creating object from state for attribute '{attr_name}'")
        return attr_type.from_state(attr_val)  # type: ignore
    elif not make and hasattr(attr_type, "get_state"):
        print(f"[DEBUG] Getting state for attribute '{attr_name}'")
        return attr_val.get_state()

    if origin in (list, collections.abc.Sequence):
        (T,) = typing.get_args(attr_type)
        return [_process(x, T, attr_name, make) for x in attr_val]  # type: ignore
    elif origin is tuple:
        Ts = typing.get_args(attr_type)
        if len(Ts) != len(attr_val):
            print(f"[ERROR] Invalid data for {attr_name}. Expected {Ts}, got {attr_val}.")
            raise ValueError(
                f"Invalid data for {attr_name}. Expected {Ts}, got {attr_val}."
            )
        return tuple(_process(x, T, attr_name, make) for T, x in zip(Ts, attr_val))  # type: ignore
    elif origin is dict:
        k_cls, v_cls = typing.get_args(attr_type)
        return {
            _process(k, k_cls, attr_name, make): _process(v, v_cls, attr_name, make)
            for k, v in attr_val.items()
        }  # type: ignore
    elif attr_type in (int, float, str, bytes, bool):
        if not isinstance(attr_val, attr_type):
            print(f"[ERROR] Invalid value for {attr_name}. Expected {attr_type}, got {attr_val} ({type(attr_val)}).")
            raise ValueError(
                f"Invalid value for {attr_name}. Expected {attr_type}, got {attr_val} ({type(attr_val)})."
            )
        return attr_type(attr_val)  # type: ignore
    elif isinstance(attr_type, type) and issubclass(attr_type, enum.Enum):
        return attr_type(attr_val) if make else attr_val.value  # type: ignore
    else:
        print(f"[ERROR] Unexpected type for {attr_name}: {attr_type!r}")
        raise TypeError(f"Unexpected type for {attr_name}: {attr_type!r}")


def _to_val(state: Any, attr_type: type[U], attr_name: str) -> U:
    """
    Create an object from the given state.
    """
    print(f"[DEBUG] Converting state to value for attribute '{attr_name}'")
    return _process(state, attr_type, attr_name, True)


def _to_state(value: Any, attr_type: type[U], attr_name: str) -> U:
    """
    Get the state of the given object.
    """
    print(f"[DEBUG] Converting value to state for attribute '{attr_name}'")
    return _process(value, attr_type, attr_name, False)


__all__ = ["Serializable", "SerializableDataclass"]