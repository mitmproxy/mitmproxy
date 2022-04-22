from unittest.mock import Mock
from mitmproxy.addons.grpc_protoc import GrpcProtocConsoleDescriptorProvider
from mitmproxy.contentviews.grpc_protoc import ViewGrpcProtoc
from mitmproxy.test import taddons, tflow, tutils


class TestViewGrpcProtoc():

    def test_render_priority(self):
        addon = ViewGrpcProtoc(Mock())

        option_addon = GrpcProtocConsoleDescriptorProvider(Mock())

        with taddons.context(option_addon) as context:
            # To configure the option addon, because ViewGrpcProtoc depends on it.
            context.configure(addon, proto_descriptor_file="file")

            is_1_when_all_conditions_are_satisfied = addon.render_priority(data=b"1234", content_type="application/grpc")
            assert is_1_when_all_conditions_are_satisfied == 1

            is_0_when_data_is_empty = addon.render_priority(data=b"", content_type="application/grpc")
            assert is_0_when_data_is_empty == 0

            is_0_when_content_type_is_unsupported = addon.render_priority(data=b"1234", content_type="application/json")
            assert is_0_when_content_type_is_unsupported == 0

            context.configure(addon, proto_descriptor_file=None)
            is_0_when_descriptor_file_is_not_set = addon.render_priority(data=b"1234", content_type="application/grpc")
            assert is_0_when_descriptor_file_is_not_set == 0

    def test_call_when_message_is_available(self):
        serializer = Mock()
        serializer.deserialize.return_value = "1234"
        addon = ViewGrpcProtoc(serializer)

        request = tutils.treq()
        result = addon.__call__(data=b"1234", flow=tflow.tflow(req=request), http_message=request)

        assert result[0] is ViewGrpcProtoc.name
        assert next(result[1])[0][1] == "1234"

        serializer.deserialize.assert_called()
        assert str(request) in str(serializer.deserialize.call_args_list)
        assert request.path in str(serializer.deserialize.call_args_list)
        assert str(b"1234") in str(serializer.deserialize.call_args_list)

    def test_call_when_message_is_none(self):
        serializer = Mock()
        addon = ViewGrpcProtoc(serializer)

        request = tutils.treq()
        result = addon.__call__(data=b"1234", flow=tflow.tflow(req=request), http_message=None)

        assert result[0] is ViewGrpcProtoc.name
        assert result[1] == ""

    def test_call_when_request_is_none(self):
        serializer = Mock()
        addon = ViewGrpcProtoc(serializer)

        request = tutils.treq()
        result = addon.__call__(data=b"1234", flow=None, http_message=request)

        assert result[0] is ViewGrpcProtoc.name
        assert result[1] == ""