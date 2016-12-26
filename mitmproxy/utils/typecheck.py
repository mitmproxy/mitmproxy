import typing
import sys


def check_type(attr_name: str, value: typing.Any, typeinfo: type) -> None:
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
        attr_name,
        type(value)
    ))

    typename = str(typeinfo)

    if typename.startswith("typing.Union"):
        if sys.version_info < (3, 6):
            types = typeinfo.__union_params__
        else:
            types = typeinfo.__args__

        for T in types:
            try:
                check_type(attr_name, value, T)
            except TypeError:
                pass
            else:
                return
        raise e
    elif typename.startswith("typing.Tuple"):
        if sys.version_info < (3, 6):
            types = typeinfo.__tuple_params__
        else:
            types = typeinfo.__args__

        if not isinstance(value, (tuple, list)):
            raise e
        if len(types) != len(value):
            raise e
        for i, (x, T) in enumerate(zip(value, types)):
            check_type("{}[{}]".format(attr_name, i), x, T)
        return
    elif typename.startswith("typing.Sequence"):
        T = typeinfo.__args__[0]
        if not isinstance(value, (tuple, list)):
            raise e
        for v in value:
            check_type(attr_name, v, T)
    elif typename.startswith("typing.IO"):
        if hasattr(value, "read"):
            return
    elif not isinstance(value, typeinfo):
        raise e


def get_arg_type_from_constructor_annotation(cls: type, attr: str) -> typing.Optional[type]:
    """
    Returns the first type annotation for attr in the class hierarchy.
    """
    for c in cls.mro():
        if attr in getattr(c.__init__, "__annotations__", ()):
            return c.__init__.__annotations__[attr]
