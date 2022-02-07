from unittest.mock import Mock, patch
from mitmproxy.addons.grpc_protoc import GrpcProtocConsoleDescriptorProvider

from mitmproxy.test import taddons

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