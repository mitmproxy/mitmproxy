import io
import typing
from unittest import mock
import pytest

from mitmproxy.utils import typecheck


class TBase:
    def __init__(self, bar: int):
        pass


class T(TBase):
    def __init__(self, foo: str):
        super(T, self).__init__(42)


def test_check_option_type():
    typecheck.check_option_type("foo", 42, int)
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", 42, str)
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", None, str)
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", b"foo", str)


def test_check_union():
    typecheck.check_option_type("foo", 42, typing.Union[int, str])
    typecheck.check_option_type("foo", "42", typing.Union[int, str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", [], typing.Union[int, str])

    # Python 3.5 only defines __union_params__
    m = mock.Mock()
    m.__str__ = lambda self: "typing.Union"
    m.__union_params__ = (int,)
    typecheck.check_option_type("foo", 42, m)


def test_check_tuple():
    typecheck.check_option_type("foo", (42, "42"), typing.Tuple[int, str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", None, typing.Tuple[int, str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", (), typing.Tuple[int, str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", (42, 42), typing.Tuple[int, str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", ("42", 42), typing.Tuple[int, str])

    # Python 3.5 only defines __tuple_params__
    m = mock.Mock()
    m.__str__ = lambda self: "typing.Tuple"
    m.__tuple_params__ = (int, str)
    typecheck.check_option_type("foo", (42, "42"), m)


def test_check_sequence():
    typecheck.check_option_type("foo", [10], typing.Sequence[int])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", ["foo"], typing.Sequence[int])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", [10, "foo"], typing.Sequence[int])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", [b"foo"], typing.Sequence[str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", "foo", typing.Sequence[str])

    # Python 3.5 only defines __parameters__
    m = mock.Mock()
    m.__str__ = lambda self: "typing.Sequence"
    m.__parameters__ = (int,)
    typecheck.check_option_type("foo", [10], m)


def test_check_io():
    typecheck.check_option_type("foo", io.StringIO(), typing.IO[str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", "foo", typing.IO[str])


def test_check_any():
    typecheck.check_option_type("foo", 42, typing.Any)
    typecheck.check_option_type("foo", object(), typing.Any)
    typecheck.check_option_type("foo", None, typing.Any)


def test_typesec_to_str():
    assert(typecheck.typespec_to_str(str)) == "str"
    assert(typecheck.typespec_to_str(typing.Sequence[str])) == "sequence of str"
    assert(typecheck.typespec_to_str(typing.Optional[str])) == "optional str"
    with pytest.raises(NotImplementedError):
        typecheck.typespec_to_str(dict)
