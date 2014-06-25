from netlib import utils
import socket

def test_hexdump():
    assert utils.hexdump("one\0"*10)


def test_cleanBin():
    assert utils.cleanBin("one") == "one"
    assert utils.cleanBin("\00ne") == ".ne"
    assert utils.cleanBin("\nne") == "\nne"
    assert utils.cleanBin("\nne", True) == ".ne"

def test_ntop_pton():
    for family, ip_string, packed_ip in (
            (socket.AF_INET,
             "127.0.0.1",
             "\x7f\x00\x00\x01"),
            (socket.AF_INET6,
             "2001:0db8:85a3:08d3:1319:8a2e:0370:7344",
             " \x01\r\xb8\x85\xa3\x08\xd3\x13\x19\x8a.\x03psD")):
        assert ip_string == utils.inet_ntop(family, packed_ip)
        assert packed_ip == utils.inet_pton(family, ip_string)
        if hasattr(socket, "inet_ntop"):
            ntop, pton = socket.inet_ntop, socket.inet_pton
            delattr(socket,"inet_ntop")
            delattr(socket,"inet_pton")
            assert ip_string == utils.inet_ntop(family, packed_ip)
            assert packed_ip == utils.inet_pton(family, ip_string)
            socket.inet_ntop, socket.inet_pton = ntop, pton