from mitmproxy.addons import core
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy import exceptions
import pytest
from unittest import mock


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


def test_replay():
    sa = core.Core()
    with taddons.context():
        f = tflow.tflow()
        with mock.patch("mitmproxy.master.Master.replay_request") as rp:
            sa.replay(f)
            assert rp.called


def test_kill():
    sa = core.Core()
    with taddons.context():
        f = tflow.tflow()
        f.intercept()
        assert f.killable
        sa.kill([f])
        assert not f.killable
