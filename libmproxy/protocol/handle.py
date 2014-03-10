from . import http, tcp

protocols = {
    'http': dict(handler=http.HTTPHandler, flow=http.HTTPFlow),
    'tcp': dict(handler=tcp.TCPHandler)
}  # PyCharm type hinting behaves bad if this is a dict constructor...


def _handler(conntype, connection_handler):
    if conntype in protocols:
        return protocols[conntype]["handler"](connection_handler)

    raise NotImplementedError   # pragma: nocover


def handle_messages(conntype, connection_handler):
    return _handler(conntype, connection_handler).handle_messages()


def handle_error(conntype, connection_handler, error):
    return _handler(conntype, connection_handler).handle_error(error)