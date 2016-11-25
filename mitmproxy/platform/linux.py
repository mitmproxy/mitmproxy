import socket
import struct

# Python socket module does not have this constant
SO_ORIGINAL_DST = 80


def original_addr(csock: socket.socket):
    odestdata = csock.getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, 16)
    _, port, a1, a2, a3, a4 = struct.unpack("!HHBBBBxxxxxxxx", odestdata)
    address = "%d.%d.%d.%d" % (a1, a2, a3, a4)
    return address, port
