import asyncio
import socket

async def udp_server():
    udp_server_address = 'localhost'
    udp_server_port = 12345

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((udp_server_address, udp_server_port))

    print(f"UDP server listening on {udp_server_address}:{udp_server_port}")

    try:
        while True:
            data, addr = udp_socket.recvfrom(1024)
            asyncio.ensure_future(handle_dns_request(data, addr, udp_socket))
    except asyncio.CancelledError:
        udp_socket.close()

async def handle_dns_request(data, addr, udp_socket):
    try:
        query = data.decode()
        print(f"Received DNS query: {query}")

        if query == "example.com":
            response = "192.168.1.1"
        else:
            response = "127.0.0.1"

        udp_socket.sendto(response.encode(), addr)
        print(f"Sent DNS response: {response}")
    except Exception as e:
        print("Error handling DNS request:", e)

async def main():
    await udp_server()

if __name__ == "__main__":
    asyncio.run(main())
