import abc
import collections.abc
import dataclasses
import enum
import typing
import uuid
from functools import cache
from typing import TypeVar

try:
    from types import NoneType
    from types import UnionType
except ImportError:  # pragma: no cover

    class UnionType:  # type: ignore
        pass

    NoneType = type(None)  # type: ignore

T = TypeVar("T", bound="Serializable")

State = typing.Any


class Serializable(metaclass=abc.ABCMeta):
    """
    Abstract Base Class that defines an API to save an object's state and restore it later on.
    """

    @classmethod
    @abc.abstractmethod
    def from_state(cls: type[T], state) -> T:
        """
        Create a new object from the given state.
        Consumes the passed state.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_state(self) -> State:
        """
        Retrieve object state.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def set_state(self, state):
        """
        Set object state to the given state. Consumes the passed state.
        May return a `dataclasses.FrozenInstanceError` if the object is immutable.
        """
        raise NotImplementedError()

    def copy(self: T) -> T:
        state = self.get_state()
        if isinstance(state, dict) and "id" in state:
            state["id"] = str(uuid.uuid4())
        return self.from_state(state)


U = TypeVar("U", bound="SerializableDataclass")


class SerializableDataclass(Serializable):
    @classmethod
    @cache
    def __fields(cls) -> tuple[dataclasses.Field, ...]:
        # with from __future__ import annotations, `field.type` is a string,
        # see https://github.com/python/cpython/issues/83623.
        hints = typing.get_type_hints(cls)
        fields = []
        # noinspection PyDataclass
        for field in dataclasses.fields(cls):  # type: ignore[arg-type]
            if field.metadata.get("serialize", True) is False:
                continue
            if isinstance(field.type, str):
                field.type = hints[field.name]
            fields.append(field)
        return tuple(fields)

    def get_state(self) -> State:
        state: dict[str, State] = {}
        for field in self.__fields():
            val = getattr(self, field.name)
            state[field.name] = _to_state(val, field.type, field.name)
        return state

    @classmethod
    def from_state(cls: type[U], state) -> U:
        # state = state.copy()
        for field in cls.__fields():
            state[field.name] = _to_val(state[field.name], field.type, field.name)
        try:
            return cls(**state)  # type: ignore
        except TypeError as e:
            raise ValueError(f"Invalid state for {cls}: {e} ({state=})") from e

    def set_state(self, state: State) -> None:
        for field in self.__fields():
            current = getattr(self, field.name)
            f_state = state.pop(field.name)
            if isinstance(current, Serializable) and f_state is not None:
                try:
                    current.set_state(f_state)
                    continue
                except dataclasses.FrozenInstanceError:
                    pass
            val: typing.Any = _to_val(f_state, field.type, field.name)
            try:
                setattr(self, field.name, val)
            except dataclasses.FrozenInstanceError:
                state[field.name] = f_state  # restore state dict.
                raise

        if state:
            raise ValueError(
                f"Unexpected fields in {type(self).__name__}.set_state: {state}"
            )


def _process(
    attr_val: typing.Any, attr_type: typing.Any, attr_name: str, make: bool
) -> typing.Any:
    origin = typing.get_origin(attr_type)
    if origin is typing.Literal:
        if attr_val not in typing.get_args(attr_type):
            raise ValueError(
                f"Invalid value for {attr_name}: {attr_val!r} does not match any literal value."
            )
        return attr_val
    if origin in (UnionType, typing.Union):
        attr_type, nt = typing.get_args(attr_type)
        assert nt is NoneType, (
            f"{attr_name}: only `x | None` union types are supported`"
        )
        if attr_val is None:
            return None  # type: ignore
        else:
            return _process(attr_val, attr_type, attr_name, make)
    else:
        if attr_val is None:
            raise ValueError(f"Attribute {attr_name} must not be None.")

    if make and hasattr(attr_type, "from_state"):
        return attr_type.from_state(attr_val)  # type: ignore
    elif not make and hasattr(attr_type, "get_state"):
        return attr_val.get_state()

    if origin in (list, collections.abc.Sequence):
        (T,) = typing.get_args(attr_type)
        return [_process(x, T, attr_name, make) for x in attr_val]  # type: ignore
    elif origin is tuple:
        # We don't have a good way to represent tuple[str,int] | tuple[str,int,int,int], so we do a dirty hack here.
        if attr_name in ("peername", "sockname"):
            return tuple(
                _process(x, T, attr_name, make)
                for x, T in zip(attr_val, [str, int, int, int])
            )  # type: ignore
        Ts = typing.get_args(attr_type)
        if len(Ts) != len(attr_val):
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
    elif attr_type in (int, float):
        if not isinstance(attr_val, (int, float)):
            raise ValueError(
                f"Invalid value for {attr_name}. Expected {attr_type}, got {attr_val} ({type(attr_val)})."
            )
        return attr_type(attr_val)  # type: ignore
    elif attr_type in (str, bytes, bool):
        if not isinstance(attr_val, attr_type):
            raise ValueError(
                f"Invalid value for {attr_name}. Expected {attr_type}, got {attr_val} ({type(attr_val)})."
            )
        return attr_type(attr_val)  # type: ignore
    elif isinstance(attr_type, type) and issubclass(attr_type, enum.Enum):
        if make:
            return attr_type(attr_val)  # type: ignore
        else:
            return attr_val.value
    else:
        raise TypeError(f"Unexpected type for {attr_name}: {attr_type!r}")


def _to_val(state: typing.Any, attr_type: typing.Any, attr_name: str) -> typing.Any:
    """Create an object based on the state given in val."""
    return _process(state, attr_type, attr_name, True)


def _to_state(value: typing.Any, attr_type: typing.Any, attr_name: str) -> typing.Any:
    """Get the state of the object given as val."""
    return _process(value, attr_type, attr_name, False)
