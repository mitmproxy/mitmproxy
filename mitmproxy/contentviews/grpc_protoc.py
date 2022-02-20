from typing import Optional
from mitmproxy import ctx, flow, http
from mitmproxy.addons.grpc_protoc import GrpcProtocConsoleDescriptorProvider
from mitmproxy.contentviews import base
from mitmproxy.utils.protoc import ProtocSerializer


class ViewGrpcProtoc(base.View):
    """
    Content view that displays deserialized protobuf content in form of a JSON.
    This content view will take the highest render priority if following conditions are met:
    1. Body contains data.
    2. The content type is 'application/grpc'.
    2. Descriptor file is set. See `GrpcProtocConsoleDescriptorProvider` for more info.
    """

    name = "gRPC/Protocol Buffer using protoc"

    __content_types_grpc = [
        "application/grpc",
    ]

    def __init__(self, serializer: ProtocSerializer) -> None:
        self.serializer = serializer

    def __call__(
        self,
        data: bytes,
        *,
        content_type: Optional[str] = None,
        flow = None,
        http_message: Optional[http.Message] = None,
        **unknown_metadata
    ):
        if http_message is not None:
            deserialized = self.serializer.deserialize(http_message, flow.request.path, data)
            return self.name, base.format_text(deserialized)
        else:
            return self.name, ""

    def render_priority(
        self,
        data: bytes,
        *,
        content_type: Optional[str] = None,
        flow: Optional[flow.Flow] = None,
        http_message: Optional[http.Message] = None,
        **unknown_metadata
    ) -> float:
        if (
            ctx.options.__contains__(GrpcProtocConsoleDescriptorProvider.option_name) and
            ctx.options.proto_descriptor_file is not None and
            bool(data) and
            content_type in self.__content_types_grpc
        ):
            return 1
        else:
            return 0