class Connection:
    address = None  # type: tuple
    connected = None  # type: bool

    def __repr__(self):
        return "{}({})".format(type(self).__name__, repr(self.__dict__))


class Client(Connection):
    def __init__(self, address):
        self.address = address
        self.connected = True


class Server(Connection):
    def __init__(self, address):
        self.address = address
        self.connected = False


class Context:
    """
    For every proxy connection/session, there is exactly one single client connection.
    """

    client = None  # type: Client

    def __init__(self, client: Client) -> None:
        self.client = client


class ClientServerContext(Context):
    """
    In most cases, there's also only exactly one server.
    """

    server = None  # type: Server

    def __init__(self, client: Client, server: Server) -> None:
        super().__init__(client)
        self.server = server
