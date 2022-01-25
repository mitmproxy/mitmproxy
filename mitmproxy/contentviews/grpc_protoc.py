from typing import Optional
from mitmproxy import contentviews, ctx, flow, http
from mitmproxy.contentviews import base
from mitmproxy.utils.protoc import ProtocSerializer


class ViewProtocGrpc(base.View):

    name = "gRPC/Protocol Buffer using protoc"

    __content_types_grpc = [
        "application/grpc",
    ]

    def __init__(self, serializer: ProtocSerializer) -> None:
        super().__init__()
        self.serializer = serializer

    def __call__(
        self,
        data: bytes,
        *,
        content_type: Optional[str] = None,
        flow: Optional[flow.Flow] = None,
        http_message: Optional[http.Message] = None,
        **unknown_metadata
    ) -> contentviews.TViewResult:

        # Fix this
        deserialized = self.serializer.deserialize(http_message, flow.request.path, data)
        return self.name, base.format_text(deserialized)

    def render_priority(
        self,
        data: bytes,
        *,
        content_type: Optional[str] = None,
        flow: Optional[flow.Flow] = None,
        http_message: Optional[http.Message] = None,
        **unknown_metadata
    ) -> float:
        # Set to high priority if a descriptor file is set and the content type is protobuf
        if ctx.options.descriptor_file is not None and bool(data) and content_type in self.__content_types_grpc:
            return 1
        else:
            return 0