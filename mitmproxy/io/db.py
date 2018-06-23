import sqlite3
from mitmproxy.io import protobuf


class DbHandler:

    """
    This class is wrapping up connection to SQLITE DB.
    """

    def __init__(self, db_path="tmp.sqlite"):
        self.db_path = db_path
        self._con = sqlite3.connect(self.db_path)
        self._c = self._con.cursor()
        self._create_db()

    def _create_db(self):
        with self._con:
            self._con.execute('CREATE TABLE IF NOT EXISTS FLOWS('
                              'id INTEGER PRIMARY KEY AUTOINCREMENT,'
                              'pbuf_blob BLOB)')

    def store(self, flows):
        blobs = []
        for flow in flows:
            blobs.append(protobuf.dumps(flow))
        with self._con:
            self._con.executemany('INSERT INTO FLOWS values (?)', blobs)

    def load(self):
        self._c.execute('SELECT * FROM FLOWS')
        return self._c.fetchall()
