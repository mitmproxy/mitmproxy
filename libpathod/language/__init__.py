import time

import pyparsing as pp

from . import http, websockets, writer, exceptions

from exceptions import *
from base import Settings
assert Settings  # prevent pyflakes from messing with this


def parse_pathod(s):
    """
        May raise ParseException
    """
    try:
        s = s.decode("ascii")
    except UnicodeError:
        raise exceptions.ParseException("Spec must be valid ASCII.", 0, 0)
    try:
        return pp.Or(
            [
                websockets.WebsocketFrame.expr(),
                http.Response.expr(),
            ]
        ).parseString(s, parseAll=True)[0]
    except pp.ParseException as v:
        raise exceptions.ParseException(v.msg, v.line, v.col)


def parse_pathoc(s):
    """
        May raise ParseException
    """
    try:
        s = s.decode("ascii")
    except UnicodeError:
        raise exceptions.ParseException("Spec must be valid ASCII.", 0, 0)
    try:
        reqs = pp.OneOrMore(
            pp.Or(
                [
                    websockets.WebsocketClientFrame.expr(),
                    http.Request.expr(),
                ]
            )
        ).parseString(s, parseAll=True)
    except pp.ParseException as v:
        raise exceptions.ParseException(v.msg, v.line, v.col)
    expanded = []
    for i in reqs:
        if i.times:
            for j in range(int(i.times.value)):
                expanded.append(i.strike_token("times"))
        else:
            expanded.append(i)
    return expanded


def parse_websocket_frame(s):
    try:
        return websockets.WebsocketFrame.expr().parseString(
            s,
            parseAll = True
        )[0]
    except pp.ParseException as v:
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

    actions = sorted(msg.actions[:])
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
