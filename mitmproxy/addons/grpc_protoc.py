from typing import Optional, Sequence
from mitmproxy import ctx, command, types
from mitmproxy.exceptions import CommandError
from mitmproxy.tools.console.master import ConsoleMaster
from mitmproxy.utils import strutils
from mitmproxy.utils.protoc import ProtocSerializer


class GrpcProtocConsoleBodyModifer:
    """
    Command options that allow for modification of protobuf content in HTTP body.
    """

    def __init__(
        self,
        serializer: ProtocSerializer,
        console_master: ConsoleMaster
    ) -> None:
        self.serializer = serializer
        self.console_master = console_master

    @command.command("console.edit.grpc.options")
    def edit_focus_options(self) -> Sequence[str]:
        focus_options = [
            "request-body",
            "response-body",
        ]

        return focus_options

    @command.command("console.edit.grpc")
    @command.argument("flow_part", type=types.Choice("console.edit.grpc.options"))
    def edit_focus(self, flow_part: str, flow) -> None:
        if not flow:
            raise CommandError("No flow selected.")

        if flow_part == "request-body":
            http_message = flow.request
        elif flow_part == "response-body":
            http_message = flow.response
        else:
            raise CommandError(f"Unsupported options {flow_part}.")

        content = http_message.get_content(strict=False) or b""

        try:
            deserialized_content = self.serializer.deserialize(http_message, flow.request.path, content)
        except ValueError as e:
            raise CommandError("Failed to deserialize the content") from e

        modified_content = self.console_master.spawn_editor(deserialized_content)

        if self.console_master.options.console_strip_trailing_newlines:
            modified_content = strutils.clean_hanging_newline(modified_content)

        try:
            http_message.content = self.serializer.serialize(http_message, flow.request.path, modified_content)
        except ValueError as e:
            raise CommandError("Failed to serialize the content") from e


class GrpcProtocConsoleDescriptorProvider:
    """
    Adds a parameter that allows to specify a proto descriptor file.
    """

    option_name = "proto_descriptor_file"

    def __init__(self, serializer: ProtocSerializer) -> None:
        self.serializer = serializer

    def load(self, loader):
        loader.add_option(
            self.option_name, Optional[str], None,
            """
            Path to the proto descriptor file.
            This argument is required in order to enable "gRPC/Protocol Buffer using protoc" content view.
            """
        )

    def configure(self, updates):
        if (
            GrpcProtocConsoleDescriptorProvider.option_name in updates and
            ctx.options.__contains__(self.option_name) and
            ctx.options.proto_descriptor_file is not None
        ):
            self.serializer.set_descriptor(ctx.options.proto_descriptor_file)