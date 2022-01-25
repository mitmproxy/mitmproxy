from typing import Optional, Sequence
from mitmproxy import ctx, command, types
from mitmproxy.utils import strutils
from mitmproxy.utils.protoc import ProtocSerializer


class GrpcProtobufModifierAddon:

    def __init__(self, serializer: ProtocSerializer) -> None:
        super.__init__()
        self.serializer = serializer

    @command.command("grpc.options")
    def edit_focus_options(self) -> Sequence[str]:
        focus_options = [
            "request body",
            "response body",
        ]

        return focus_options

    @command.command("grpc")
    @command.argument("flow_part", type=types.Choice("grpc.options"))
    def edit_focus(self, flow_part: str) -> None:
        request = ctx.master.view.focus.flow.request
        response = ctx.master.view.focus.flow.response
        path = request.path

        if flow_part == "request body":
            content = request.get_content(strict=False) or b""
            http_message = request
        elif flow_part == "response body":
            content = response.get_content(strict=False) or b""
            http_message = response
        else:
            ctx.log(f"Unknown option {flow_part}")
            return

        deserialized_content = self.protobuf_modifier.deserialize(http_message, path, content)
        modifiedContent = ctx.master.spawn_editor(deserialized_content)

        if ctx.master.options.console_strip_trailing_newlines:
            modifiedContent = strutils.clean_hanging_newline(modifiedContent)

        http_message.content = self.serializer.serialize(http_message, path, modifiedContent)


class GrpcProtobufOptionAddon:

    def __init__(self, serializer: ProtocSerializer) -> None:
        self.__init__()
        self.serializer = serializer

    def load(self, loader):
        loader.add_option(
            name = "descriptor_file",
            typespec = Optional[str],
            default = None,
            help = "Set the descriptor file used for serialiation and deserialization of protobuf content",
        )

    def configure(self, updates):
        if ("descriptor_file" in updates and ctx.options.descriptor_file is not None):
            self.serializer.set_descriptor_file_path(ctx.options.descriptor_file)