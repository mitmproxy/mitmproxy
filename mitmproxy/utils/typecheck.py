import typing


def check_type(name: str, value: typing.Any, typeinfo: typing.Any) -> None:
    """
    This function checks if the provided value is an instance of typeinfo
    and raises a TypeError otherwise.

    The following types from the typing package have specialized support:

    - Union
    - Tuple
    - IO
    """
    # If we realize that we need to extend this list substantially, it may make sense
    # to use typeguard for this, but right now it's not worth the hassle for 16 lines of code.

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
                check_type(name, value, T)
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
            check_type("{}[{}]".format(name, i), x, T)
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
            check_type(name, v, T)
    elif typename.startswith("typing.IO"):
        if hasattr(value, "read"):
            return
        else:
            raise e
    elif not isinstance(value, typeinfo):
        raise e
