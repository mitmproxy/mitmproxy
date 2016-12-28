import typing

import mock
import pytest
from mitmproxy.utils import typecheck


class TBase:
    def __init__(self, bar: int):
        pass


class T(TBase):
    def __init__(self, foo: str):
        super(T, self).__init__(42)


def test_get_arg_type_from_constructor_annotation():
    assert typecheck.get_arg_type_from_constructor_annotation(T, "foo") == str
    assert typecheck.get_arg_type_from_constructor_annotation(T, "bar") == int
    assert not typecheck.get_arg_type_from_constructor_annotation(T, "baz")


def test_check_type():
    typecheck.check_type("foo", 42, int)
    with pytest.raises(TypeError):
        typecheck.check_type("foo", 42, str)
    with pytest.raises(TypeError):
        typecheck.check_type("foo", None, str)
    with pytest.raises(TypeError):
        typecheck.check_type("foo", b"foo", str)


def test_check_union():
    typecheck.check_type("foo", 42, typing.Union[int, str])
    typecheck.check_type("foo", "42", typing.Union[int, str])
    with pytest.raises(TypeError):
        typecheck.check_type("foo", [], typing.Union[int, str])


def test_check_tuple():
    with pytest.raises(TypeError):
        typecheck.check_type("foo", None, typing.Tuple[int, str])
    with pytest.raises(TypeError):
        typecheck.check_type("foo", (), typing.Tuple[int, str])
    with pytest.raises(TypeError):
        typecheck.check_type("foo", (42, 42), typing.Tuple[int, str])
    with pytest.raises(TypeError):
        typecheck.check_type("foo", ("42", 42), typing.Tuple[int, str])
    typecheck.check_type("foo", (42, "42"), typing.Tuple[int, str])


def test_check_sequence():
    typecheck.check_type("foo", [10], typing.Sequence[int])
    with pytest.raises(TypeError):
        typecheck.check_type("foo", ["foo"], typing.Sequence[int])
    with pytest.raises(TypeError):
        typecheck.check_type("foo", [10, "foo"], typing.Sequence[int])
    with pytest.raises(TypeError):
        typecheck.check_type("foo", [b"foo"], typing.Sequence[str])
    with pytest.raises(TypeError):
        typecheck.check_type("foo", "foo", typing.Sequence[str])

    # Python 3.5.0 only defines __parameters__
    m = mock.Mock()
    m.__str__ = lambda self: "typing.Sequence"
    m.__parameters__ = (int,)
    typecheck.check_type("foo", [10], m)
