from google.protobuf.descriptor_pb2 import FileDescriptorSet
from google.protobuf.descriptor import MethodDescriptor
from google.protobuf.descriptor_pool import DescriptorPool
from google.protobuf.message_factory import MessageFactory
from google.protobuf.message import DecodeError
from google.protobuf.text_format import MessageToString, Parse, ParseError

import mitmproxy
import mitmproxy.http


class ProtocSerializer:
    """
    Wrapper around google protobuf package that provides serialization and deserialization of protobuf content.
    The implementation uses a proto descriptor to resolve messages. Method resolution works based on HTTP path.

    NOTE: Content compression is not supported.
    """

    def __init__(self) -> None:
        self.descriptor_pool = DescriptorPool()

    def set_descriptor(self, descriptor_path: str) -> None:
        with open(descriptor_path, mode="rb") as file:
            descriptor = FileDescriptorSet.FromString(file.read())
            for proto in descriptor.file:
                self.descriptor_pool.Add(proto)

            self.message_factory = MessageFactory(self.descriptor_pool)

    def deserialize(self, http_message: mitmproxy.http.Message, path: str, serialized_protobuf: bytes) -> str:
        """
        Takes a protobuf byte array and returns a deserialized string in text format.
        You must set a descriptor file must prior to calling this method.
        The string is formatted according to `google.protobuf.text_format`

        Raises:
            ValueError - in case deserialization fails because the method could not be resolved or the input data is invalid.
        """

        grpc_method = self.__find_method_by_path(path)
        # Strip the length and compression header; 5 bytes in total.
        # Payload compression is not supported at the moment.
        data_without_prefix = serialized_protobuf[5:]

        if isinstance(http_message, mitmproxy.http.Request):
            message = self.message_factory.GetPrototype(grpc_method.input_type)()
        elif isinstance(http_message, mitmproxy.http.Response):
            message = self.message_factory.GetPrototype(grpc_method.output_type)()
        else:
            raise ValueError(f"Unexpected HTTP message type {http_message}")

        message.Clear()

        try:
            message.MergeFromString(data_without_prefix)
        except DecodeError as e:
            raise ValueError("Unable to deserialize input") from e

        return MessageToString(
            message=message,
            descriptor_pool=self.descriptor_pool,
            print_unknown_fields=True,
        )

    def serialize(self, http_message: mitmproxy.http.Message, path: str, text: str) -> bytes:
        """
        Takes a string and serializes it into a protobuf byte array.
        You must set a descriptor file must prior to calling this method.
        The string must be formatted according `google.protobuf.text_format`

        Raises:
            ValueError - in case serialization fails because the method could not be resolved or the input data is invalid
                         e.g. unknown fields present or invalid text format.
        """

        grpc_method = self.__find_method_by_path(path)

        if isinstance(http_message, mitmproxy.http.Request):
            empty_message = self.message_factory.GetPrototype(grpc_method.input_type)()
        elif isinstance(http_message, mitmproxy.http.Response):
            empty_message = self.message_factory.GetPrototype(grpc_method.output_type)()
        else:
            raise ValueError(f"Unexpected HTTP message type {http_message}")

        empty_message.Clear()

        try:
            populated_message = Parse(
                text=text,
                message=empty_message,
                allow_field_number=True,
                allow_unknown_field=False,
                descriptor_pool=self.descriptor_pool
            )
        except ParseError as e:
            raise ValueError("Unable to serialize input") from e

        serializedMessage = populated_message.SerializeToString(deterministic=True)
        # Prepend the length and compression header; 5 bytes in total in big endian order.
        # Payload compression is not supported at the moment, so compression bit is always 0.
        return len(serializedMessage).to_bytes(5, "big") + serializedMessage

    def __find_method_by_path(self, path: str) -> MethodDescriptor:
        try:
            # Drop the first '/' from the path and convert the rest to a fully qualified namespace that we can look up.
            method_path = path.replace("/", ".")[1:]
            return self.descriptor_pool.FindMethodByName(method_path)
        except KeyError as e:
            raise ValueError("Failed to resolve method name by path") from e


serializer = ProtocSerializer()