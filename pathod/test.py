from six.moves import cStringIO as StringIO
import threading
import time

from six.moves import queue

from . import pathod


class Daemon:
    IFACE = "127.0.0.1"

    def __init__(self, ssl=None, **daemonargs):
        self.q = queue.Queue()
        self.logfp = StringIO()
        daemonargs["logfp"] = self.logfp
        self.thread = _PaThread(self.IFACE, self.q, ssl, daemonargs)
        self.thread.start()
        self.port = self.q.get(True, 5)
        self.urlbase = "%s://%s:%s" % (
            "https" if ssl else "http",
            self.IFACE,
            self.port
        )

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.logfp.truncate(0)
        self.shutdown()
        return False

    def p(self, spec):
        """
            Return a URL that will render the response in spec.
        """
        return "%s/p/%s" % (self.urlbase, spec)

    def text_log(self):
        return self.logfp.getvalue()

    def expect_log(self, n, timeout=5):
        l = []
        start = time.time()
        while True:
            l = self.log()
            if time.time() - start >= timeout:
                return None
            if len(l) >= n:
                break
        return l

    def last_log(self):
        """
            Returns the last logged request, or None.
        """
        l = self.expect_log(1)
        if not l:
            return None
        return l[0]

    def log(self):
        """
            Return the log buffer as a list of dictionaries.
        """
        return self.thread.server.get_log()

    def clear_log(self):
        """
            Clear the log.
        """
        return self.thread.server.clear_log()

    def shutdown(self):
        """
            Shut the daemon down, return after the thread has exited.
        """
        self.thread.server.shutdown()
        self.thread.join()


class _PaThread(threading.Thread):

    def __init__(self, iface, q, ssl, daemonargs):
        threading.Thread.__init__(self)
        self.name = "PathodThread"
        self.iface, self.q, self.ssl = iface, q, ssl
        self.daemonargs = daemonargs
        self.server = None

    def run(self):
        self.server = pathod.Pathod(
            (self.iface, 0),
            ssl=self.ssl,
            **self.daemonargs
        )
        self.name = "PathodThread (%s:%s)" % (
            self.server.address.host,
            self.server.address.port
        )
        self.q.put(self.server.address.port)
        self.server.serve_forever()
