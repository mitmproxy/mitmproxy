import time

import contrib.pyparsing as pp

from . import base, http, websockets, writer, exceptions

from exceptions import *


class Settings:
    def __init__(
        self,
        staticdir = None,
        unconstrained_file_access = False,
        request_host = None,
        websocket_key = None
    ):
        self.staticdir = staticdir
        self.unconstrained_file_access = unconstrained_file_access
        self.request_host = request_host
        self.websocket_key = websocket_key


def parse_response(s):
    """
        May raise ParseException
    """
    try:
        s = s.decode("ascii")
    except UnicodeError:
        raise exceptions.ParseException("Spec must be valid ASCII.", 0, 0)
    try:
        return http.Response.expr().parseString(s, parseAll=True)[0]
    except pp.ParseException, v:
        raise exceptions.ParseException(v.msg, v.line, v.col)


def parse_requests(s):
    """
        May raise ParseException
    """
    try:
        s = s.decode("ascii")
    except UnicodeError:
        raise exceptions.ParseException("Spec must be valid ASCII.", 0, 0)
    try:
        return pp.OneOrMore(
            pp.Or(
                [
                    websockets.WebsocketFrame.expr(),
                    http.Request.expr(),
                ]
            )
        ).parseString(s, parseAll=True)
    except pp.ParseException, v:
        raise exceptions.ParseException(v.msg, v.line, v.col)


def serve(msg, fp, settings):
    """
        fp: The file pointer to write to.

        request_host: If this a request, this is the connecting host. If
        None, we assume it's a response. Used to decide what standard
        modifications to make if raw is not set.

        Calling this function may modify the object.
    """
    msg = msg.resolve(settings)
    started = time.time()

    vals = msg.values(settings)
    vals.reverse()

    actions = msg.actions[:]
    actions.sort()
    actions.reverse()
    actions = [i.intermediate(settings) for i in actions]

    disconnect = writer.write_values(fp, vals, actions[:])
    duration = time.time() - started
    ret = dict(
        disconnect = disconnect,
        started = started,
        duration = duration,
    )
    ret.update(msg.log(settings))
    return ret
