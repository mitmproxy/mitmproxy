from __future__ import absolute_import, print_function, division
import copy

from mitmproxy import options
from mitmproxy import exceptions
from netlib.tutils import raises


class TO(options.Options):
    attributes = [
        "one",
        "two"
    ]


def test_options():
    o = TO(two="three")
    assert o.one is None
    assert o.two == "three"
    o.one = "one"
    assert o.one == "one"
    raises("no such option", setattr, o, "nonexistent", "value")
    raises("no such option", o.update, nonexistent = "value")

    rec = []

    def sub(opts):
        rec.append(copy.copy(opts))

    o.changed.connect(sub)

    o.one = "ninety"
    assert len(rec) == 1
    assert rec[-1].one == "ninety"

    o.update(one="oink")
    assert len(rec) == 2
    assert rec[-1].one == "oink"


def test_rollback():
    o = TO(one="two")

    rec = []

    def sub(opts):
        rec.append(copy.copy(opts))

    recerr = []

    def errsub(opts, **kwargs):
        recerr.append(kwargs)

    def err(opts):
        if opts.one == "ten":
            raise exceptions.OptionsError

    o.changed.connect(sub)
    o.changed.connect(err)
    o.errored.connect(errsub)

    o.one = "ten"
    assert isinstance(recerr[0]["exc"], exceptions.OptionsError)
    assert o.one == "two"
    assert len(rec) == 2
    assert rec[0].one == "ten"
    assert rec[1].one == "two"
