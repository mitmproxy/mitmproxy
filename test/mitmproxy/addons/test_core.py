from mitmproxy.addons import core
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy import exceptions
import pytest


def test_set():
    sa = core.Core()
    with taddons.context() as tctx:
        tctx.master.addons.add(sa)

        assert not tctx.master.options.anticomp
        tctx.command(sa.set, "anticomp")
        assert tctx.master.options.anticomp

        with pytest.raises(exceptions.CommandError):
            tctx.command(sa.set, "nonexistent")


def test_resume():
    sa = core.Core()
    with taddons.context():
        f = tflow.tflow()
        assert not sa.resume([f])
        f.intercept()
        sa.resume([f])
        assert not f.reply.state == "taken"


def test_mark():
    sa = core.Core()
    with taddons.context():
        f = tflow.tflow()
        assert not f.marked
        sa.mark([f], True)
        assert f.marked

        sa.mark_toggle([f])
        assert not f.marked
        sa.mark_toggle([f])
        assert f.marked
