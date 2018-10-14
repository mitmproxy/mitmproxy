import typing

Type = typing.Union[
    typing.Any  # anything more elaborate really fails with mypy at the moment.
]


def sequence_type(typeinfo: typing.Type[typing.List]) -> Type:
    """Return the type of a sequence, e.g. typing.List"""
    return typeinfo.__args__[0]  # type: ignore


def tuple_types(typeinfo: typing.Type[typing.Tuple]) -> typing.Sequence[Type]:
    """Return the types of a typing.Tuple"""
    return typeinfo.__args__  # type: ignore


def union_types(typeinfo: typing.Type[typing.Tuple]) -> typing.Sequence[Type]:
    """return the types of a typing.Union"""
    return typeinfo.__args__  # type: ignore


def mapping_types(typeinfo: typing.Type[typing.Mapping]) -> typing.Tuple[Type, Type]:
    """return the types of a mapping, e.g. typing.Dict"""
    return typeinfo.__args__  # type: ignore


def check_option_type(name: str, value: typing.Any, typeinfo: Type) -> None:
    """
    Check if the provided value is an instance of typeinfo and raises a
    TypeError otherwise. This function supports only those types required for
    options.
    """
    e = TypeError("Expected {} for {}, but got {}.".format(
        typeinfo,
        name,
        type(value)
    ))

    typename = str(typeinfo)

    if typename.startswith("typing.Union"):
        for T in union_types(typeinfo):
            try:
                check_option_type(name, value, T)
            except TypeError:
                pass
            else:
                return
        raise e
    elif typename.startswith("typing.Tuple"):
        types = tuple_types(typeinfo)
        if not isinstance(value, (tuple, list)):
            raise e
        if len(types) != len(value):
            raise e
        for i, (x, T) in enumerate(zip(value, types)):
            check_option_type("{}[{}]".format(name, i), x, T)
        return
    elif typename.startswith("typing.Sequence"):
        T = sequence_type(typeinfo)
        if not isinstance(value, (tuple, list)):
            raise e
        for v in value:
            check_option_type(name, v, T)
    elif typename.startswith("typing.IO"):
        if hasattr(value, "read"):
            return
        else:
            raise e
    elif typename.startswith("typing.Any"):
        return
    elif not isinstance(value, typeinfo):
        raise e


def typespec_to_str(typespec: typing.Any) -> str:
    if typespec in (str, int, bool):
        t = typespec.__name__
    elif typespec == typing.Optional[str]:
        t = 'optional str'
    elif typespec == typing.Sequence[str]:
        t = 'sequence of str'
    else:
        raise NotImplementedError
    return t
