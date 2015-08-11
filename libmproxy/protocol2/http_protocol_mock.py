"""
Temporary mock to sort out API discrepancies
"""
from netlib.http.http1 import HTTP1Protocol


class HTTP1(object):
    @staticmethod
    def read_request(connection, *args, **kwargs):
        """
        :type connection: object
        """
        return HTTP1Protocol(connection).read_request(*args, **kwargs)