class Connection:
    """
    Connections exposed to the layers only contain metadata, no socket objects.
    """
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
    Layers get a context object that has all contextual information they require.
    For now, the only required property is the client connection, with ClientServerContext
    adding the server connection.

    TODO: We may just use a simple context class that has _all_ attributes we ever think of?
    Alternatively, we could have a `.get(attr)`, that mimicks what the transparent attribute
    lookup did in the previous implementation.
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
