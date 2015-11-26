import os
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

_observers = {}


def watch(script, callback):
    if script in _observers:
        raise RuntimeError("Script already observed")
    script_dir = os.path.dirname(os.path.abspath(script.args[0]))
    event_handler = _ScriptModificationHandler(callback)
    observer = Observer()
    observer.schedule(event_handler, script_dir)
    observer.start()
    _observers[script] = observer


def unwatch(script):
    observer = _observers.pop(script, None)
    if observer:
        observer.stop()
        observer.join()


class _ScriptModificationHandler(PatternMatchingEventHandler):
    def __init__(self, callback):
        # We could enumerate all relevant *.py files (as werkzeug does it),
        # but our case looks like it isn't as simple as enumerating sys.modules.
        # This should be good enough for now.
        super(_ScriptModificationHandler, self).__init__(
            ignore_directories=True,
            patterns=["*.py"]
        )
        self.callback = callback

    def on_modified(self, event):
        self.callback()

__all__ = ["watch", "unwatch"]