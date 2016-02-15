import itertools
import time

import pyparsing as pp

from . import http, http2, websockets, writer, exceptions

from exceptions import *
from base import Settings
assert Settings  # prevent pyflakes from messing with this


def expand(msg):
    times = getattr(msg, "times", None)
    if times:
        for j_ in xrange(int(times.value)):
            yield msg.strike_token("times")
    else:
        yield msg


def parse_pathod(s, use_http2=False):
    """
        May raise ParseException
    """
    try:
        s = s.decode("ascii")
    except UnicodeError:
        raise exceptions.ParseException("Spec must be valid ASCII.", 0, 0)
    try:
        if use_http2:
            expressions = [
                # http2.Frame.expr(),
                http2.Response.expr(),
            ]
        else:
            expressions = [
                websockets.WebsocketFrame.expr(),
                http.Response.expr(),
            ]
        reqs = pp.Or(expressions).parseString(s, parseAll=True)
    except pp.ParseException as v:
        raise exceptions.ParseException(v.msg, v.line, v.col)
    return itertools.chain(*[expand(i) for i in reqs])


def parse_pathoc(s, use_http2=False):
    try:
        s = s.decode("ascii")
    except UnicodeError:
        raise exceptions.ParseException("Spec must be valid ASCII.", 0, 0)
    try:
        if use_http2:
            expressions = [
                # http2.Frame.expr(),
                http2.Request.expr(),
            ]
        else:
            expressions = [
                websockets.WebsocketClientFrame.expr(),
                http.Request.expr(),
            ]
        reqs = pp.OneOrMore(pp.Or(expressions)).parseString(s, parseAll=True)
    except pp.ParseException as v:
        raise exceptions.ParseException(v.msg, v.line, v.col)
    return itertools.chain(*[expand(i) for i in reqs])


def parse_websocket_frame(s):
    """
        May raise ParseException
    """
    try:
        reqs = pp.OneOrMore(
            websockets.WebsocketFrame.expr()
        ).parseString(
            s,
            parseAll=True
        )
    except pp.ParseException as v:
        raise exceptions.ParseException(v.msg, v.line, v.col)
    return itertools.chain(*[expand(i) for i in reqs])


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
        disconnect=disconnect,
        started=started,
        duration=duration,
    )
    ret.update(msg.log(settings))
    return ret
