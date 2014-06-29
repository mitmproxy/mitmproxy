import struct
import socket
import os
import fcntl

class Resolver:
    DIOCNATLOOK=0xc0544417
    PF_INOUT=0
    def __init__(self):
        self.natfd= os.open("/dev/pf", os.O_RDWR)

    def original_addr(self, csock):
        peer = csock.getpeername()
        sock = csock.getsockname()
        nl= self.makenatlook(peer, sock)
        rnl= fcntl.ioctl(self.natfd, Resolver.DIOCNATLOOK, nl)
        orig= self.unpacknatlook(rnl)
        return orig[0], orig[1]

    def makenatlook(self,afrom, ato):
        return struct.pack("!16s16s16s16s4s4s4s4sBBBB", 
                self.makepfaddr(afrom[0]), self.makepfaddr(ato[0]), "", "",
                self.makepfport(afrom[1]), self.makepfport(ato[1]), "", "",
                socket.AF_INET, socket.IPPROTO_TCP, 0, Resolver.PF_INOUT)
    def unpacknatlook(self,nl):
        _, _, _, rdaddr, _, _, _, rdport, _, _, _, _= struct.unpack("!16s16s16s16s4s4s4s4sBBBB", nl)
        return (self.unpackpfaddr(rdaddr), self.unpackpfport(rdport))

    def makepfaddr(self,a):
        return struct.pack("!BBBB", *[int(x) for x in a.split(".")])
    def unpackpfaddr(self,a):
        return "%d.%d.%d.%d" % struct.unpack("!BBBB", a[:4])

    def makepfport(self,p):
        return struct.pack("!H", p)
    def unpackpfport(self,p):
        return struct.unpack("!H", p[:2])[0]


