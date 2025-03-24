import socket


def get_free_port() -> int:
    """
    Get a port that's free for both TCP and UDP.
    """
    for _ in range(10):
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            tcp.bind(("", 0))
            port: int = tcp.getsockname()[1]
            udp.bind(("", port))
            udp.close()
            return port
        except OSError:
            pass
        finally:
            tcp.close()

    return 0
