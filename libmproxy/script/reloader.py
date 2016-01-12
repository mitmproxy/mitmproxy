import os
import fnmatch
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers.polling import PollingObserver 

_observers = {}


def watch(script, callback):
    if script in _observers:
        raise RuntimeError("Script already observed")
    script_dir = os.path.dirname(os.path.abspath(script.args[0]))
    script_name = os.path.basename(script.args[0])
    event_handler = _ScriptModificationHandler(callback, filename=script_name)
    observer = PollingObserver()
    observer.schedule(event_handler, script_dir)
    observer.start()
    _observers[script] = observer


def unwatch(script):
    observer = _observers.pop(script, None)
    if observer:
        observer.stop()
        observer.join()


class _ScriptModificationHandler(PatternMatchingEventHandler):
    def __init__(self, callback, filename='*'):

        super(_ScriptModificationHandler, self).__init__(
            ignore_directories=True,
        )
        self.callback = callback
        self.filename = filename 

    def on_modified(self, event):
        if event.is_directory:
            files_in_dir = [event.src_path + "/" + 
                    f for f in os.listdir(event.src_path)]
            if len(files_in_dir) > 0:
                modified_filepath = max(files_in_dir, key=os.path.getmtime)
            else:
                return
        else:
            modified_filepath = event.src_path

        if fnmatch.fnmatch(os.path.basename(modified_filepath), self.filename):
            self.callback()

    def on_created(self, event):
        if fnmatch.fnmatch(os.path.basename(event.src_path), self.filename):
            self.callback()

__all__ = ["watch", "unwatch"]

