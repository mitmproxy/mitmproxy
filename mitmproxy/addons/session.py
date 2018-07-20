import os
import sqlite3

from mitmproxy.exceptions import SessionLoadException
from mitmproxy.utils.data import pkg_data


# Could be implemented using async libraries
class SessionDB:
    """
    This class wraps connection to DB
    for Sessions and handles creation,
    retrieving and insertion in tables.
    """

    def __init__(self, db_path=None):
        """
        Connect to an already existing database,
        or create a new one with optional path.
        :param db_path:
        """
        if db_path is not None and os.path.isfile(db_path):
            self._load_session(db_path)
        else:
            path = db_path or 'tmp.sqlite'
            # in case tmp.sqlite already exists in FS
            if os.path.isfile(path):
                os.remove(path)
            self.con = sqlite3.connect(path)
            script_path = pkg_data.path("io/sql/session_create.sql")
            qry = open(script_path, 'r').read()
            with self.con:
                self.con.executescript(qry)

    def _load_session(self, path):
        if not self.is_session_db(path):
            raise SessionLoadException('Given path does not point to a valid Session')
        self.con = sqlite3.connect(path)

    @staticmethod
    def is_session_db(path):
        """
        Check if database entered from user
        is a valid Session SQLite DB.
        :return: True if valid, False if invalid.
        """
        try:
            c = sqlite3.connect(f'file:{path}?mode=rw', uri=True)
            cursor = c.cursor()
            cursor.execute("SELECT NAME FROM sqlite_master WHERE type='table';")
            rows = cursor.fetchall()
            tables = [('FLOW',), ('BODY',), ('META',), ('ANNOTATION',)]
            if all(elem in rows for elem in tables):
                c.close()
                return True
        except:
            if c:
                c.close()
        return False
