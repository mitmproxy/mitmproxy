from . import urwid_escape
import urwid.escape


def patch():
    """
    backport of urwid 2.1's fix for https://github.com/mitmproxy/mitmproxy/issues/3765

    this can be removed once we upgrade to a newer urwid stable release,
    see https://github.com/urwid/urwid/issues/403
    """

    for attr in dir(urwid_escape):
        setattr(urwid.escape, attr, getattr(urwid_escape, attr))
