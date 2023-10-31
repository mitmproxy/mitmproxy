import io
import typing
from collections.abc import Sequence
from typing import Any
from typing import Optional
from typing import TextIO
from typing import Union

import pytest

from mitmproxy.utils import typecheck


class TBase:
    def __init__(self, bar: int):
        pass


class T(TBase):
    def __init__(self, foo: str):
        super().__init__(42)


def test_check_option_type():
    typecheck.check_option_type("foo", 42, int)
    typecheck.check_option_type("foo", 42, float)
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", 42, str)
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", None, str)
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", b"foo", str)


def test_check_union():
    typecheck.check_option_type("foo", 42, Union[int, str])
    typecheck.check_option_type("foo", "42", Union[int, str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", [], Union[int, str])


def test_check_tuple():
    typecheck.check_option_type("foo", (42, "42"), tuple[int, str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", None, tuple[int, str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", (), tuple[int, str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", (42, 42), tuple[int, str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", ("42", 42), tuple[int, str])


def test_check_sequence():
    typecheck.check_option_type("foo", [10], Sequence[int])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", ["foo"], Sequence[int])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", [10, "foo"], Sequence[int])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", [b"foo"], Sequence[str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", "foo", Sequence[str])


def test_check_io():
    typecheck.check_option_type("foo", io.StringIO(), TextIO)
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", "foo", TextIO)


def test_check_any():
    typecheck.check_option_type("foo", 42, Any)
    typecheck.check_option_type("foo", object(), Any)
    typecheck.check_option_type("foo", None, Any)


def test_typesec_to_str():
    assert (typecheck.typespec_to_str(str)) == "str"
    assert (typecheck.typespec_to_str(Sequence[str])) == "sequence of str"
    assert (typecheck.typespec_to_str(Optional[str])) == "optional str"
    assert (typecheck.typespec_to_str(Optional[int])) == "optional int"
    with pytest.raises(NotImplementedError):
        typecheck.typespec_to_str(dict)


def test_typing_aliases():
    assert (typecheck.typespec_to_str(typing.Sequence[str])) == "sequence of str"
    typecheck.check_option_type("foo", [10], typing.Sequence[int])
    typecheck.check_option_type("foo", (42, "42"), tuple[int, str])
