import io

import pyshark
from kaitaistruct import KaitaiStream
from scapy.all import PcapReader, Raw

import tls_client_hello

packets = pyshark.FileCapture("tls-handshake-dump.pcap")
with PcapReader('tls-handshake-dump.pcap') as pcap_reader:
    for pkt_pcap, pkt in zip(pcap_reader, packets):
        try:
            ssl = pkt.ssl
        except AttributeError:  # TCP Retransmission packet
            continue

        ch_bytes = bytes(pkt_pcap.getlayer(Raw))[9:]  # Remove headers
        client_hello = tls_client_hello.TlsClientHello(KaitaiStream(io.BytesIO(bytes(ch_bytes))))

        # Version
        assert(int(ssl.handshake_version.raw_value[:2]) == client_hello.version.major)
        assert(int(ssl.handshake_version.raw_value[2:]) == client_hello.version.minor)

        # Random
        assert(ssl.handshake_random_time.hex_value == client_hello.random.gmt_unix_time)
        assert(bytes.fromhex(ssl.handshake_random.raw_value) == client_hello.random.random)

        # Session Id
        assert(int(ssl.handshake_session_id_length) == client_hello.session_id.len)
        try:
            assert(bytes.fromhex(ssl.handshake_session_id.raw_value) == client_hello.session_id.sid)
        except AttributeError:
            if not int(ssl.handshake_session_id_length):
                pass
            else:
                raise Exception

        # Cipher Suites
        assert(int(ssl.handshake_cipher_suites_length) == client_hello.cipher_suites.len)
        for cs1, cs2 in zip(ssl.handshake_ciphersuite.fields, client_hello.cipher_suites.cipher_suites):
            assert(cs1.hex_value == cs2.cipher_suite)

        # Compression methods
        assert(int(ssl.handshake_comp_methods_length) == client_hello.compression_methods.len)
        assert(bytes.fromhex(ssl.handshake_comp_method.raw_value) == client_hello.compression_methods.compression_methods)

        # Extensions
        assert(int(ssl.handshake_extensions_length) == client_hello.extensions.len)

        for ext_len1, ext_len2 in zip(ssl.handshake_extension_len.fields, client_hello.extensions.extensions):
            assert(ext_len1.hex_value == ext_len2.len)

        for ext1, ext2 in zip(ssl.handshake_extension_type.fields, client_hello.extensions.extensions):
            assert(ext1.hex_value == ext2.type)
            if ext2.type == 0:
                sni = ext2
            elif ext2.type == 16:
                alpn = ext2

        # SNI
        assert(int(ssl.handshake_extensions_server_name_list_len) == sni.body.list_length)

        assert(int(ssl.handshake_extensions_server_name_type) == sni.body.server_names[0].name_type)
        assert(ssl.handshake_extensions_server_name == str(sni.body.server_names[0].host_name, 'idna'))

        # ALPN
        assert(int(ssl.handshake_extensions_alpn_len) == alpn.body.ext_len)

        for pname1, pname2 in zip(ssl.handshake_extensions_alpn_str.all_fields, alpn.body.alpn_protocols):
            assert(pname1.show == pname2.name.decode())
