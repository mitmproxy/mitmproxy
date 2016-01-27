"""
The mitmproxy script context provides an API to inline scripts.
"""
from __future__ import absolute_import, print_function, division
from .. import contentviews


class ScriptContext(object):

    """
    The script context should be used to interact with the global mitmproxy state from within a
    script.
    """

    def __init__(self, master):
        self._master = master

    def log(self, message, level="info"):
        """
        Logs an event.

        By default, only events with level "error" get displayed. This can be controlled with the "-v" switch.
        How log messages are handled depends on the front-end. mitmdump will print them to stdout,
        mitmproxy sends output to the eventlog for display ("e" keyboard shortcut).
        """
        self._master.add_event(message, level)

    def kill_flow(self, f):
        """
        Kills a flow immediately. No further data will be sent to the client or the server.
        """
        f.kill(self._master)

    def duplicate_flow(self, f):
        """
        Returns a duplicate of the specified flow. The flow is also
        injected into the current state, and is ready for editing, replay,
        etc.
        """
        self._master.pause_scripts = True
        f = self._master.duplicate_flow(f)
        self._master.pause_scripts = False
        return f

    def replay_request(self, f):
        """
        Replay the request on the current flow. The response will be added
        to the flow object.
        """
        return self._master.replay_request(f, block=True, run_scripthooks=False)

    @property
    def app_registry(self):
        return self._master.apps

    def add_contentview(self, view_obj):
        contentviews.add(view_obj)

    def remove_contentview(self, view_obj):
        contentviews.remove(view_obj)
