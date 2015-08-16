"""
Temporary mock to sort out API discrepancies
"""
from libmproxy.protocol.http_wrappers import HTTPResponse, HTTPRequest
from netlib.http.http1 import HTTP1Protocol


class HTTP1(object):
    @staticmethod
    def read_request(connection, *args, **kwargs):
        """
        :type connection: object
        """
        return HTTPRequest.from_protocol(HTTP1Protocol(connection), *args, **kwargs)

    @staticmethod
    def read_response(connection, *args, **kwargs):
        """
        :type connection: object
        """
        return HTTPResponse.from_protocol(HTTP1Protocol(connection), *args, **kwargs)

    @staticmethod
    def read_http_body(connection, *args, **kwargs):
        """
        :type connection: object
        """
        return HTTP1Protocol(connection).read_http_body(*args, **kwargs)


    @staticmethod
    def _assemble_response_first_line(*args, **kwargs):
        return HTTP1Protocol()._assemble_response_first_line(*args, **kwargs)


    @staticmethod
    def _assemble_response_headers(*args, **kwargs):
        return HTTP1Protocol()._assemble_response_headers(*args, **kwargs)


    @staticmethod
    def read_http_body_chunked(connection, *args, **kwargs):
        """
        :type connection: object
        """
        return HTTP1Protocol(connection).read_http_body_chunked(*args, **kwargs)

    @staticmethod
    def assemble(*args, **kwargs):
        return HTTP1Protocol().assemble(*args, **kwargs)