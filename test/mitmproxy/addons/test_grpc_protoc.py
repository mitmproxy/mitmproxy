import unittest
from unittest.mock import Mock
from mitmproxy.addons.grpc_protoc import GrpcProtocConsoleBodyModifer, GrpcProtocConsoleDescriptorProvider

from mitmproxy.test import taddons, tflow
from mitmproxy.test.tutils import treq, tresp
from mitmproxy.exceptions import CommandError


class TestGrpcProtocConsoleBodyModifier(unittest.TestCase):

    def test_edit_focus_options(self):
        addon = GrpcProtocConsoleBodyModifer(Mock(), Mock())

        assert ["request-body", "response-body"] == addon.edit_focus_options()

    def test_edit_focus_request_body(self):
        serializer = Mock()
        serializer.serialize.return_value = b"1234"
        master = Mock()
        master.spawn_editor.return_value = "modifiedMessage"
        addon = GrpcProtocConsoleBodyModifer(serializer, master)

        flow = tflow.tflow(req=treq(content=b"message"))
        addon.edit_focus("request-body", flow)

        serializer.deserialize.assert_called()
        assert str(flow.request) in str(serializer.deserialize.call_args_list)
        assert flow.request.path in str(serializer.deserialize.call_args_list)
        assert str(b"message") in str(serializer.deserialize.call_args_list)

        serializer.serialize.assert_called()
        assert str(flow.request) in str(serializer.serialize.call_args_list)
        assert flow.request.path in str(serializer.serialize.call_args_list)

        assert flow.request.content == b"1234"

    def test_edit_focus_response_body(self):
        serializer = Mock()
        serializer.serialize.return_value = b"1234"
        master = Mock()
        master.spawn_editor.return_value = "modifiedMessage"
        addon = GrpcProtocConsoleBodyModifer(serializer, master)

        flow = tflow.tflow(resp=tresp(content=b"message"))
        addon.edit_focus("response-body", flow)

        serializer.deserialize.assert_called()
        assert str(flow.response) in str(serializer.deserialize.call_args_list)
        assert flow.request.path in str(serializer.deserialize.call_args_list)
        assert str(b"message") in str(serializer.deserialize.call_args_list)

        serializer.serialize.assert_called()
        assert str(flow.response) in str(serializer.serialize.call_args_list)
        assert flow.request.path in str(serializer.serialize.call_args_list)

        assert flow.response.content == b"1234"

    def test_edit_focus_flow_not_set(self):
        addon = GrpcProtocConsoleBodyModifer(Mock(), Mock())

        with self.assertRaises(CommandError):
            addon.edit_focus("request-body", None)

    def test_edit_focus_unknown_option(self):
        addon = GrpcProtocConsoleBodyModifer(Mock(), Mock())

        with self.assertRaises(CommandError):
            addon.edit_focus("random-option", tflow.tflow())

    def test_edit_focus_deserialization_fails(self):
        serializer = Mock()
        serializer.deserialize.side_effect = ValueError()
        master = Mock()
        master.spawn_editor.return_value = "modifiedMessage"
        addon = GrpcProtocConsoleBodyModifer(serializer, master)

        with self.assertRaises(CommandError):
            addon.edit_focus("request-body", tflow.tflow())

    def test_edit_focus_serialization_fails(self):
        serializer = Mock()
        serializer.serialize.side_effect = ValueError()
        master = Mock()
        master.spawn_editor.return_value = "modifiedMessage"
        addon = GrpcProtocConsoleBodyModifer(serializer, master)

        with self.assertRaises(CommandError):
            addon.edit_focus("request-body", tflow.tflow())


class TestGrpcProtocConsoleDescriptorProvider:

    def test_configure(self):
        serializer = Mock()
        addon = GrpcProtocConsoleDescriptorProvider(serializer)

        with taddons.context(addon) as context:
            context.configure(addon, proto_descriptor_file="file")

            serializer.set_descriptor.assert_called()
            assert "file" in str(serializer.set_descriptor.call_args_list)

    def test_do_not_configure_when_option_is_not_in_updates(self):
        serializer = Mock()
        addon = GrpcProtocConsoleDescriptorProvider(serializer)

        with taddons.context(addon) as context:
            context.configure(addon)

            serializer.set_descriptor.assert_not_called()