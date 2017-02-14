import socketserver
from time import sleep


class service(socketserver.BaseRequestHandler):

    def handle(self):
        data = 'dummy'
        print("Client connected with ", self.client_address)
        while True:
            self.request.send(
                "HTTP/1.1 200 OK\r\nConnection: close\r\nContent-Length: 7\r\n\r\ncontent")
            data = self.request.recv(1024)
            if not len(data):
                print("Connection closed by remote: ", self.client_address)
                sleep(3600)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


server = ThreadedTCPServer(('', 1520), service)
server.serve_forever()
