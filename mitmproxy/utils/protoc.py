import google.protobuf.descriptor_pb2 as protobuf_descriptor_pb2
import google.protobuf.reflection as protobuf_reflection
import google.protobuf.descriptor as protobuf_descriptor
import google.protobuf.json_format as protobuf_json
import google.protobuf.descriptor_pool as protobuf_descriptor_pool

import mitmproxy


class ProtocSerializer:
    """
    Wrapper around google protobuf package that provides serialization and deserialization of protobuf content.
    The implementation uses a proto descriptor to resolve messages. Method resolution works based on HTTP path. 

    NOTE: Content compression is not supported. 
    """

    def __init__(self) -> None:
        self.descriptor_pool = protobuf_descriptor_pool.DescriptorPool()

    def set_descriptor(self, descriptor_path: str) -> None:
        with open(descriptor_path, mode="rb") as file:
            descriptor = protobuf_descriptor_pb2.FileDescriptorSet.FromString(file.read())
            for proto in descriptor.file:
                self.descriptor_pool.Add(proto)

    def deserialize(self, http_message: mitmproxy.http.Message, path: str, serialized_protobuf: bytes) -> str:
        """
        Takes a protobuf byte array and returns a deserialized JSON string. 
        This method requires a descriptor file.
        """

        grpc_method = self.__find_method_by_path(path)
        # Strip the length and compression header; 5 bytes in total.
        # Payload compression is not supported at the moment.
        data_without_prefix = serialized_protobuf[5:]

        if isinstance(http_message, mitmproxy.http.Request):
            # ParseMessage is deprecated, update to GetPrototype
            message = protobuf_reflection.ParseMessage(grpc_method.input_type, data_without_prefix)
        elif isinstance(http_message, mitmproxy.http.Response):
            message = protobuf_reflection.ParseMessage(grpc_method.output_type, data_without_prefix)
        else:
            raise Exception(f"Unexpected HTTP message type {http_message}")

        return protobuf_json.MessageToJson(message=message, descriptor_pool=self.descriptor_pool)

    def serialize(self, http_message: mitmproxy.http.Message, path: str, json: str) -> bytes:
        """
        Takes a JSON string and serializes it into a protobuf byte array.
        This method requires a descriptor file.
        """
        
        grpc_method = self.__find_method_by_path(path)

        if isinstance(http_message, mitmproxy.http.Request):
            empty_message = protobuf_reflection.ParseMessage(grpc_method.input_type, b"")
            populated_message = protobuf_json.Parse(
                text=json,
                message=empty_message,
                ignore_unknown_fields=True,
                descriptor_pool=self.descriptor_pool)
        elif isinstance(http_message, mitmproxy.http.Response):
            empty_message = protobuf_reflection.ParseMessage(grpc_method.output_type, b"")
            populated_message = protobuf_json.Parse(
                text=json,
                message=empty_message,
                ignore_unknown_fields=True,
                descriptor_pool=self.descriptor_pool)
        else:
            raise Exception(f"Unexpected HTTP message type {http_message}")

        serializedMessage = populated_message.SerializeToString()
        # Prepend the length and compression header; 5 bytes in total in big endian order.
        # Payload compression is not supported at the moment, so compression bit is always 0.
        return len(serializedMessage).to_bytes(5, "big") + serializedMessage

    def __find_method_by_path(self, path: str) -> protobuf_descriptor.MethodDescriptor:
        # Drop the first '/' from the path and convert the rest to a fully qualified namespace that we can look up.
        method_path = path.replace("/", ".")[1:]
        return self.descriptor_pool.FindMethodByName(method_path)

serializer = ProtocSerializer()