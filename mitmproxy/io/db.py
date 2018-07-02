import sqlite3
import os

from mitmproxy.io import protobuf


class DBHandler:

    """
    This class is wrapping up connection to SQLITE DB.
    """

    def __init__(self, db_path, mode='load'):
        if mode == 'write':
            if os.path.isfile(db_path):
                os.remove(db_path)
        self.db_path = db_path
        self._con = sqlite3.connect(self.db_path)
        self._c = self._con.cursor()
        self._create_db()

    def _create_db(self):
        with self._con:
            self._con.execute('CREATE TABLE IF NOT EXISTS FLOWS('
                              'id INTEGER PRIMARY KEY,'
                              'pbuf_blob BLOB)')

    def store(self, flows):
        blobs = []
        for flow in flows:
            blobs.append((protobuf.dumps(flow),))
        with self._con:
            self._con.executemany('INSERT INTO FLOWS (pbuf_blob) values (?)', blobs)

    def load(self):
        flows = []
        self._c.execute('SELECT pbuf_blob FROM FLOWS')
        for row in self._c.fetchall():
            flows.append((protobuf.loads(row[0])))
        return flows
