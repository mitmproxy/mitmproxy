import binascii
import unittest
from mitmproxy.utils.protoc import ProtocSerializer
from mitmproxy.test import tutils


class TestProtocSerializer(unittest.TestCase):

    def test_deserialize_request(self):
        serializer = ProtocSerializer()
        serializer.set_descriptor("test/mitmproxy/utils/test_grpc_data/test.descriptor")

        deserialized = serializer.deserialize(
            http_message=tutils.treq(),
            path="/mitmproxy/test/utils/test_grpc_data/TestService/GetUser",
            serialized_protobuf=binascii.unhexlify("00000000060a0454657374")
        )

        assert deserialized.replace(" ", "").replace("\n", "") == 'name:"Test"'

    def test_deserialize_request_with_unknown_fields(self):
        serializer = ProtocSerializer()
        serializer.set_descriptor("test/mitmproxy/utils/test_grpc_data/test.descriptor")

        deserialized = serializer.deserialize(
            http_message=tutils.treq(),
            path="/mitmproxy/test/utils/test_grpc_data/TestService/GetUser",
            serialized_protobuf=binascii.unhexlify("00000000080a04546573741803")
        )

        assert deserialized.replace(" ", "").replace("\n", "") == 'name:"Test"3:3'

    def test_deserialize_response(self):
        serializer = ProtocSerializer()
        serializer.set_descriptor("test/mitmproxy/utils/test_grpc_data/test.descriptor")

        deserialized = serializer.deserialize(
            http_message=tutils.tresp(),
            path="/mitmproxy/test/utils/test_grpc_data/TestService/GetUser",
            serialized_protobuf=binascii.unhexlify("000000000a0a045465737410021803")
        )

        assert deserialized.replace(" ", "").replace("\n", "") == 'name:"Test"age:2id:3'

    def test_deserialize_unknown_path(self):
        with self.assertRaises(ValueError):
            serializer = ProtocSerializer()
            serializer.set_descriptor("test/mitmproxy/utils/test_grpc_data/test.descriptor")

            serializer.deserialize(
                http_message=tutils.treq(),
                path="path/unknown",
                serialized_protobuf=b"1234"
            )

    def test_deserialize_invalid_data(self):
        with self.assertRaises(ValueError):
            serializer = ProtocSerializer()
            serializer.set_descriptor("test/mitmproxy/utils/test_grpc_data/test.descriptor")

            serializer.deserialize(
                http_message=tutils.treq(),
                path="/mitmproxy/test/utils/test_grpc_data/TestService/GetUser",
                serialized_protobuf=b"invalidData"
            )

    def test_serialize_request(self):
        serializer = ProtocSerializer()
        serializer.set_descriptor("test/mitmproxy/utils/test_grpc_data/test.descriptor")

        serialized = serializer.serialize(
            http_message=tutils.treq(),
            path="/mitmproxy/test/utils/test_grpc_data/TestService/GetUser",
            text='name: "Test"'
        )

        assert serialized == binascii.unhexlify("00000000060a0454657374")

    def test_serialize_response(self):
        serializer = ProtocSerializer()
        serializer.set_descriptor("test/mitmproxy/utils/test_grpc_data/test.descriptor")

        serialized = serializer.serialize(
            http_message=tutils.tresp(),
            path="/mitmproxy/test/utils/test_grpc_data/TestService/GetUser",
            text='name: "Test" age:2 id:3'
        )

        assert serialized == binascii.unhexlify("000000000a0a045465737410021803")

    def test_serialize_unknown_path(self):
        with self.assertRaises(ValueError):
            serializer = ProtocSerializer()
            serializer.set_descriptor("test/mitmproxy/utils/test_grpc_data/test.descriptor")

            serializer.serialize(
                http_message=tutils.treq(),
                path="path/unknown",
                text='name: "Test"'
            )

    def test_serialize_unknown_fields(self):
        with self.assertRaises(ValueError):
            serializer = ProtocSerializer()
            serializer.set_descriptor("test/mitmproxy/utils/test_grpc_data/test.descriptor")

            serializer.serialize(
                http_message=tutils.treq(),
                path="/mitmproxy/test/utils/test_grpc_data/TestService/GetUser",
                text='name: "Test" age:2 id:3 newField:54'
            )

    def test_serialize_invalid_text_format(self):
        with self.assertRaises(ValueError):
            serializer = ProtocSerializer()
            serializer.set_descriptor("test/mitmproxy/utils/test_grpc_data/test.descriptor")

            serializer.serialize(
                http_message=tutils.treq(),
                path="/mitmproxy/test/utils/test_grpc_data/TestService/GetUser",
                text='name: "Test" age:2 id:3,,,,,'
            )