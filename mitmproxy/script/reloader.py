from __future__ import absolute_import, print_function, division

import os

from watchdog.events import RegexMatchingEventHandler

from watchdog.observers.polling import PollingObserver as Observer
# We occasionally have watchdog errors on Windows, Linux and Mac when using the native observers.
# After reading through the watchdog source code and issue tracker,
# we may want to replace this with a very simple implementation of our own.

_observers = {}


def watch(script, callback):
    if script in _observers:
        raise RuntimeError("Script already observed")
    script_dir = os.path.dirname(os.path.abspath(script.filename))
    script_name = os.path.basename(script.filename)
    event_handler = _ScriptModificationHandler(callback, filename=script_name)
    observer = Observer()
    observer.schedule(event_handler, script_dir)
    observer.start()
    _observers[script] = observer


def unwatch(script):
    observer = _observers.pop(script, None)
    if observer:
        observer.stop()
        observer.join()


class _ScriptModificationHandler(RegexMatchingEventHandler):

    def __init__(self, callback, filename='.*'):

        super(_ScriptModificationHandler, self).__init__(
            ignore_directories=True,
            regexes=['.*' + filename]
        )
        self.callback = callback

    def on_modified(self, event):
        self.callback()

__all__ = ["watch", "unwatch"]
