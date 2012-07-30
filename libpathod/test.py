import json, threading, Queue
import requests
import pathod, utils


class Daemon:
    IFACE = "127.0.0.1"
    def __init__(self, ssl=None, **daemonargs):
        self.q = Queue.Queue()
        self.thread = _PaThread(self.IFACE, self.q, ssl, daemonargs)
        self.thread.start()
        self.port = self.q.get(True, 5)
        self.urlbase = "%s://%s:%s"%("https" if ssl else "http", self.IFACE, self.port)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.shutdown()
        return False

    def p(self, spec):
        """
            Return a URL that will render the response in spec.
        """
        return "%s/p/%s"%(self.urlbase, spec)

    def info(self):
        """
            Return some basic info about the remote daemon.
        """
        resp = requests.get("%s/api/info"%self.urlbase, verify=False)
        return resp.json

    def last_log(self):
        """
            Returns the last logged request. Raises AssertionError if no
            requests have been logged.
        """
        l = self.log()
        if not l:
            raise AssertionError("No requests logged")
        return l[-1]

    def log(self):
        """
            Return the log buffer as a list of dictionaries.
        """
        resp = requests.get("%s/api/log"%self.urlbase, verify=False)
        return resp.json["log"]

    def clear_log(self):
        """
            Clear the log.
        """
        resp = requests.get("%s/api/clear_log"%self.urlbase, verify=False)
        return resp.ok

    def shutdown(self):
        """
            Shut the daemon down, return after the thread has exited.
        """
        self.thread.server.shutdown()
        self.thread.join()


class _PaThread(threading.Thread):
    def __init__(self, iface, q, ssl, daemonargs):
        threading.Thread.__init__(self)
        self.iface, self.q, self.ssl = iface, q, ssl
        self.daemonargs = daemonargs

    def run(self):
        if self.ssl is True:
            ssloptions = dict(
                 keyfile = utils.data.path("resources/server.key"),
                 certfile = utils.data.path("resources/server.crt"),
            )
        else:
            ssloptions = self.ssl
        self.server = pathod.Pathod(
            (self.iface, 0),
            ssloptions = ssloptions,
            **self.daemonargs
        )
        self.q.put(self.server.port)
        self.server.serve_forever()
