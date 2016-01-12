import os
import fnmatch
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
    def __init__(self, callback, pattern='*.py'):
        # We could enumerate all relevant *.py files (as werkzeug does it),
        # but our case looks like it isn't as simple as enumerating sys.modules.
        # This should be good enough for now.
        super(_ScriptModificationHandler, self).__init__(
            ignore_directories=True,
        )
        self.callback = callback
        self.pattern = pattern

    def on_modified(self, event):
        super(_ScriptModificationHandler, self).on_modified(event)
        if event.is_directory:
            files_in_dir = [event.src_path + "/" + \
                    f for f in os.listdir(event.src_path)]
            if len(files_in_dir) > 0:
                modifiedFilename = max(files_in_dir, key=os.path.getmtime)
            else:
                return
        else:
            modifiedFilename = event.src_path

        if fnmatch.fnmatch(os.path.basename(modifiedFilename), self.pattern):
            self.callback()

__all__ = ["watch", "unwatch"]

