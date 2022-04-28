import socket
import struct

# Python's socket module does not have these constants
SO_ORIGINAL_DST = 80
SOL_IPV6 = 41


def original_addr(csock: socket.socket) -> tuple[str, int]:
    # Get the original destination on Linux.
    # In theory, this can be done using the following syscalls:
    #     sock.getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, 16)
    #     sock.getsockopt(SOL_IPV6, SO_ORIGINAL_DST, 28)
    #
    # In practice, it is a bit more complex:
    #  1. We cannot rely on sock.family to decide which syscall to use because of IPv4-mapped
    #     IPv6 addresses. If sock.family is AF_INET6 while sock.getsockname() is ::ffff:127.0.0.1,
    #     we need to call the IPv4 version to get a result.
    #  2. We can't just try the IPv4 syscall and then do IPv6 if that doesn't work,
    #     because doing the wrong syscall can apparently crash the whole Python runtime.
    # As such, we use a heuristic to check which syscall to do.
    is_ipv4 = "." in csock.getsockname()[0]  # either 127.0.0.1 or ::ffff:127.0.0.1
    if is_ipv4:
        # the struct returned here should only have 8 bytes, but invoking sock.getsockopt
        # with buflen=8 doesn't work.
        dst = csock.getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, 16)
        port, raw_ip = struct.unpack_from("!2xH4s", dst)
        ip = socket.inet_ntop(socket.AF_INET, raw_ip)
    else:
        dst = csock.getsockopt(SOL_IPV6, SO_ORIGINAL_DST, 28)
        port, raw_ip = struct.unpack_from("!2xH4x16s", dst)
        ip = socket.inet_ntop(socket.AF_INET6, raw_ip)
    return ip, port
