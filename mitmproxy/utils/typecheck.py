import typing


def check_type(attr_name: str, value: typing.Any, typeinfo: type) -> None:
    """
    This function checks if the provided value is an instance of typeinfo
    and raises a TypeError otherwise.

    The following types from the typing package have specialized support:

    - Union
    - Tuple
    - TextIO
    """
    # If we realize that we need to extend this list substantially, it may make sense
    # to use typeguard for this, but right now it's not worth the hassle for 16 lines of code.

    e = TypeError("Expected {} for {}, but got {}.".format(
        typeinfo,
        attr_name,
        type(value)
    ))

    if isinstance(typeinfo, typing.UnionMeta):
        for T in typeinfo.__union_params__:
            try:
                check_type(attr_name, value, T)
            except TypeError:
                pass
            else:
                return
        raise e
    if isinstance(typeinfo, typing.TupleMeta):
        check_type(attr_name, value, tuple)
        if len(typeinfo.__tuple_params__) != len(value):
            raise e
        for i, (x, T) in enumerate(zip(value, typeinfo.__tuple_params__)):
            check_type("{}[{}]".format(attr_name, i), x, T)
        return
    if typeinfo == typing.TextIO:
        if hasattr(value, "read"):
            return

    if not isinstance(value, typeinfo):
        raise e


def get_arg_type_from_constructor_annotation(cls: type, attr: str) -> typing.Optional[type]:
    """
    Returns the first type annotation for attr in the class hierarchy.
    """
    for c in cls.mro():
        if attr in getattr(c.__init__, "__annotations__", ()):
            return c.__init__.__annotations__[attr]
