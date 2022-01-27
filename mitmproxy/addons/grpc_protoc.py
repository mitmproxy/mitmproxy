from typing import Optional, Sequence
from mitmproxy import ctx, command, types
from mitmproxy.utils import strutils
from mitmproxy.utils.protoc import ProtocSerializer


class GrpcProtocConsoleBodyModifer:
    """
    Command options that allow for modification of protobuf content in HTTP body. 
    """

    def __init__(self, serializer: ProtocSerializer) -> None:
        self.serializer = serializer

    @command.command("console.edit.grpc.options")
    def edit_focus_options(self) -> Sequence[str]:
        focus_options = [
            "request-body",
            "response-body",
        ]

        return focus_options

    @command.command("console.edit.grpc")
    @command.argument("flow_part", type=types.Choice("console.edit.grpc.options"))
    def edit_focus(self, flow_part: str) -> None:
        request = ctx.master.view.focus.flow.request
        response = ctx.master.view.focus.flow.response
        path = request.path

        if flow_part == "request-body":
            http_message = request
        elif flow_part == "response-body":
            http_message = response
        else:
            return

        content = http_message.get_content(strict=False) or b""
        deserialized_content = self.serializer.deserialize(http_message, path, content)
        modified_content = ctx.master.spawn_editor(deserialized_content)

        if ctx.master.options.console_strip_trailing_newlines:
            modified_content = strutils.clean_hanging_newline(modified_content)

        http_message.content = self.serializer.serialize(http_message, path, modified_content)


class GrpcProtocConsoleDescriptorProvider:
    """
    Adds a parameter that allows to specify a proto descriptor file. 
    """

    def __init__(self, serializer: ProtocSerializer) -> None:
        self.serializer = serializer

    def load(self, loader):
        loader.add_option(
            "proto_descriptor_file", Optional[str], None,
            """
            Path to the proto descriptor file. This argument is required in order to enable "gRPC/Protocol Buffer using protoc" content view.
            """
        )

    def configure(self, updates):
        if ("proto_descriptor_file" in updates and ctx.options.proto_descriptor_file is not None):
            self.serializer.set_descriptor(ctx.options.proto_descriptor_file)