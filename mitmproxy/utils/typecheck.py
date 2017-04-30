import typing


def check_command_return_type(value: typing.Any, typeinfo: typing.Any) -> bool:
    """
    Check if the provided value is an instance of typeinfo. Returns True if the
    types match, False otherwise. This function supports only those types
    required for command return values.
    """
    typename = str(typeinfo)
    if typename.startswith("typing.Sequence"):
        try:
            T = typeinfo.__args__[0]  # type: ignore
        except AttributeError:
            # Python 3.5.0
            T = typeinfo.__parameters__[0]  # type: ignore
        if not isinstance(value, (tuple, list)):
            return False
        for v in value:
            if not check_command_return_type(v, T):
                return False
    elif typename.startswith("typing.Union"):
        try:
            types = typeinfo.__args__  # type: ignore
        except AttributeError:
            # Python 3.5.x
            types = typeinfo.__union_params__  # type: ignore
        for T in types:
            checks = [check_command_return_type(value, T) for T in types]
            if not any(checks):
                return False
    elif value is None and typeinfo is None:
        return True
    elif not isinstance(value, typeinfo):
        return False
    return True


def check_option_type(name: str, value: typing.Any, typeinfo: typing.Any) -> None:
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
        try:
            types = typeinfo.__args__  # type: ignore
        except AttributeError:
            # Python 3.5.x
            types = typeinfo.__union_params__  # type: ignore

        for T in types:
            try:
                check_option_type(name, value, T)
            except TypeError:
                pass
            else:
                return
        raise e
    elif typename.startswith("typing.Tuple"):
        try:
            types = typeinfo.__args__  # type: ignore
        except AttributeError:
            # Python 3.5.x
            types = typeinfo.__tuple_params__  # type: ignore

        if not isinstance(value, (tuple, list)):
            raise e
        if len(types) != len(value):
            raise e
        for i, (x, T) in enumerate(zip(value, types)):
            check_option_type("{}[{}]".format(name, i), x, T)
        return
    elif typename.startswith("typing.Sequence"):
        try:
            T = typeinfo.__args__[0]  # type: ignore
        except AttributeError:
            # Python 3.5.0
            T = typeinfo.__parameters__[0]  # type: ignore
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
