from unittest.mock import Mock
from mitmproxy.addons.grpc_protoc import GrpcProtocConsoleDescriptorProvider
from mitmproxy.contentviews.grpc_protoc import ViewGrpcProtoc
from mitmproxy.test import taddons, tflow, tutils


class TestViewGrpcProtoc:

    def test_render_priority(self):
        addon = ViewGrpcProtoc(Mock())

        option_addon = GrpcProtocConsoleDescriptorProvider(Mock())

        with taddons.context(option_addon) as context:
            # To configure the option addon, because ViewGrpcProtoc depends on it.
            context.configure(addon, proto_descriptor_file="file")

            render_priority = addon.render_priority(data=b"1234", content_type="application/grpc")
            assert render_priority == 1

            render_priority = addon.render_priority(data=b"", content_type="application/grpc")
            assert render_priority == 0

            render_priority = addon.render_priority(data=b"1234", content_type="application/json")
            assert render_priority == 0

            context.configure(addon, proto_descriptor_file=None)
            render_priority = addon.render_priority(data=b"1234", content_type="application/grpc")
            assert render_priority == 0

    def test_call(self):
        serializer = Mock()
        addon = ViewGrpcProtoc(serializer)

        request = tutils.treq()
        addon.__call__(data=b"1234", flow=tflow.tflow(req=request), http_message=request)

        serializer.deserialize.assert_called()
        assert str(request) in str(serializer.deserialize.call_args_list)
        assert request.path in str(serializer.deserialize.call_args_list)
        assert str(b"1234") in str(serializer.deserialize.call_args_list)