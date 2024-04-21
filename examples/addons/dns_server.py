import asyncio
import socket

class DNSProtocol:
    def __init__(self):
        self.response_received = asyncio.Event()
        self.response_data = None

    def received(self, data):
        self.response_data = data
        self.response_received.set()

class DNSServer:
    async def async_getaddrinfo(self, hostname):
        try:
            udp_server_address = 'local'
            udp_server_port = 12234

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)  # Set timeout threshold for socket operations

            try:
                sock.sendto(hostname.encode(), (udp_server_address, udp_server_port))

                data, _ = sock.recvfrom(1024)

                ip_address = data.decode()
                return ip_address
            finally:
                sock.close()
        except socket.timeout as e:
            print("Timeout waiting for data from UDP socket:", e)
            return None
        except Exception as e:
            print("Error communicating with UDP server:", e)
            return None


    async def receive_from_socket(self, sock):
        try:
            data, _ = await asyncio.wait_for(sock.recvfrom(1024), timeout=5)
            return data
        except asyncio.TimeoutError as e:
            print("Timeout waiting for data from UDP socket:", e)
            return None
        except Exception as e:
            print("Error receiving data from UDP socket:", e)
            return None
        finally:
            sock.close()

addons=[DNSServer()]
