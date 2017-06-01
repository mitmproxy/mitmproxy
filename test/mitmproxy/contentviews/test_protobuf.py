from unittest import mock
import pytest

from mitmproxy.contentviews import protobuf
from mitmproxy.test import tutils
from . import full_eval


def test_view_protobuf_request():
    v = full_eval(protobuf.ViewProtobuf())
    p = tutils.test_data.path("mitmproxy/data/protobuf01")

    with mock.patch('mitmproxy.contentviews.protobuf.ViewProtobuf.is_available'):
        with mock.patch('subprocess.Popen') as n:
            m = mock.Mock()
            attrs = {'communicate.return_value': (b'1: "3bbc333c-e61c-433b-819a-0b9a8cc103b8"', True)}
            m.configure_mock(**attrs)
            n.return_value = m

            with open(p, "rb") as f:
                data = f.read()
            content_type, output = v(data)
            assert content_type == "Protobuf"
            assert output[0] == [('text', b'1: "3bbc333c-e61c-433b-819a-0b9a8cc103b8"')]

            m.communicate = mock.MagicMock()
            m.communicate.return_value = (None, None)
            with pytest.raises(ValueError, matches="Failed to parse input."):
                v(b'foobar')


def test_view_protobuf_availability():
    with mock.patch('subprocess.Popen') as n:
        m = mock.Mock()
        attrs = {'communicate.return_value': (b'libprotoc fake version', True)}
        m.configure_mock(**attrs)
        n.return_value = m
        assert protobuf.ViewProtobuf().is_available()

        m = mock.Mock()
        attrs = {'communicate.return_value': (b'command not found', True)}
        m.configure_mock(**attrs)
        n.return_value = m
        assert not protobuf.ViewProtobuf().is_available()


def test_view_protobuf_fallback():
    with mock.patch('subprocess.Popen.communicate') as m:
        m.side_effect = OSError()
        v = full_eval(protobuf.ViewProtobuf())
        with pytest.raises(NotImplementedError, matches='protoc not found'):
            v(b'foobar')
