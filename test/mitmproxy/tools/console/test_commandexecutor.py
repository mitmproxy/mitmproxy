from unittest.mock import Mock

from mitmproxy.test import tflow
from mitmproxy.tools.console import signals
from mitmproxy.tools.console.commandexecutor import CommandExecutor


def test_command_returning_flow_list_shows_status_message(console):
    # A command that returns Sequence[flow.Flow] (e.g. `view.flows.resolve`) must not
    # be routed to the DataViewerOverlay: rendering it there deepcopies the flows,
    # which crashes with `TypeError: cannot pickle 'Context' object` for any flow
    # that carries a live connection context (mitmproxy/mitmproxy#4916). Regression
    # test for the `type(ret) == Sequence[flow.Flow]` dead-code check, which never
    # matched at runtime because Python erases generic parameters.
    executor = CommandExecutor(console)
    console.commands.execute = Mock(return_value=[tflow.tflow(), tflow.tflow()])
    console.overlay = Mock()

    messages = []

    def on_status_message(message, expire=5):
        messages.append(message)

    # connect() only keeps a weak reference, so on_status_message must stay alive
    # for the duration of the test.
    signals.status_message.connect(on_status_message)

    executor("view.flows.resolve @all")

    console.overlay.assert_not_called()
    assert messages == ["Command returned 2 flows"]


def test_command_returning_single_flow_shows_status_message(console):
    # Same dead-code class of bug: `type(ret) is flow.Flow` never matches a concrete
    # subclass like HTTPFlow, so a command returning exactly one flow also used to
    # fall through to the DataViewerOverlay instead of a short status message.
    executor = CommandExecutor(console)
    console.commands.execute = Mock(return_value=tflow.tflow())
    console.overlay = Mock()

    messages = []

    def on_status_message(message, expire=5):
        messages.append(message)

    signals.status_message.connect(on_status_message)

    executor("view.flows.resolve @focus")

    console.overlay.assert_not_called()
    assert messages == ["Command returned 1 flow"]


def test_command_returning_other_value_uses_overlay(console):
    executor = CommandExecutor(console)
    console.commands.execute = Mock(return_value=["not", "flows"])
    console.overlay = Mock()

    executor("some.command")

    console.overlay.assert_called_once()
