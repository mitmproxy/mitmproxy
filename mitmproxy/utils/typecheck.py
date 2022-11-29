import typing
from collections import abc

try:
    from types import UnionType
except ImportError:  # pragma: no cover
    UnionType = object()  # type: ignore

Type = typing.Union[
    typing.Any  # anything more elaborate really fails with mypy at the moment.
]


def check_option_type(name: str, value: typing.Any, typeinfo: Type) -> None:
    """
    Check if the provided value is an instance of typeinfo and raises a
    TypeError otherwise. This function supports only those types required for
    options.
    """
    e = TypeError(f"Expected {typeinfo} for {name}, but got {type(value)}.")

    origin = typing.get_origin(typeinfo)

    if origin is typing.Union or origin is UnionType:
        for T in typing.get_args(typeinfo):
            try:
                check_option_type(name, value, T)
            except TypeError:
                pass
            else:
                return
        raise e
    elif origin is tuple:
        types = typing.get_args(typeinfo)
        if not isinstance(value, (tuple, list)):
            raise e
        if len(types) != len(value):
            raise e
        for i, (x, T) in enumerate(zip(value, types)):
            check_option_type(f"{name}[{i}]", x, T)
        return
    elif origin is abc.Sequence:
        T = typing.get_args(typeinfo)[0]
        if not isinstance(value, (tuple, list)):
            raise e
        for v in value:
            check_option_type(name, v, T)
    elif origin is typing.IO or typeinfo in (typing.TextIO, typing.BinaryIO):
        if hasattr(value, "read"):
            return
        else:
            raise e
    elif typeinfo is typing.Any:
        return
    elif not isinstance(value, typeinfo):
        if typeinfo is float and isinstance(value, int):
            return
        raise e


def typespec_to_str(typespec: typing.Any) -> str:
    if typespec in (str, int, float, bool):
        t = typespec.__name__
    elif typespec == typing.Optional[str]:
        t = "optional str"
    elif typespec in (typing.Sequence[str], abc.Sequence[str]):
        t = "sequence of str"
    elif typespec == typing.Optional[int]:
        t = "optional int"
    else:
        raise NotImplementedError
    return t
