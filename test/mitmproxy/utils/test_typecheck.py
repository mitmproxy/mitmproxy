import io
import typing
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
    typecheck.check_option_type("foo", 42, typing.Union[int, str])
    typecheck.check_option_type("foo", "42", typing.Union[int, str])
    with pytest.raises(TypeError):
        typecheck.check_option_type("foo", [], typing.Union[int, str])


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
    assert(typecheck.typespec_to_str(typing.Optional[int])) == "optional int"
    with pytest.raises(NotImplementedError):
        typecheck.typespec_to_str(dict)


def test_mapping_types():
    # this is not covered by check_option_type, but still belongs in this module
    assert (str, int) == typecheck.mapping_types(typing.Mapping[str, int])
