import time
import threading


class BaseThread(threading.Thread):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name=name, *args, **kwargs)
        self._thread_started = time.time()

    def _threadinfo(self):
        return "%s - age: %is" % (
            self.name,
            int(time.time() - self._thread_started)
        )
