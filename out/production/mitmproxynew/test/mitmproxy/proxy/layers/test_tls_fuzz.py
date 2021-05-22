from hypothesis import given, example
from hypothesis.strategies import binary, integers

from mitmproxy.net.tls import ClientHello
from mitmproxy.proxy.layers.tls import parse_client_hello

client_hello_with_extensions = bytes.fromhex(
    "16030300bb"  # record layer
    "010000b7"  # handshake layer
    "03033b70638d2523e1cba15f8364868295305e9c52aceabda4b5147210abc783e6e1000022c02bc02fc02cc030"
    "cca9cca8cc14cc13c009c013c00ac014009c009d002f0035000a0100006cff0100010000000010000e00000b65"
    "78616d706c652e636f6d0017000000230000000d00120010060106030501050304010403020102030005000501"
    "00000000001200000010000e000c02683208687474702f312e3175500000000b00020100000a00080006001d00"
    "170018"
)


@given(i=integers(0, len(client_hello_with_extensions)), data=binary())
@example(i=183, data=b'\x00\x00\x00\x00\x00\x00\x00\x00\x00')
def test_fuzz_h2_request_chunks(i, data):
    try:
        ch = parse_client_hello(client_hello_with_extensions[:i] + data)
    except ValueError:
        pass
    else:
        assert ch is None or isinstance(ch, ClientHello)
