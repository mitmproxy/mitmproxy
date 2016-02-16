.. _models:

Models
======

.. automodule:: netlib.http

    .. autoclass:: Request

        .. rubric:: Data
        .. autoattribute:: first_line_format
        .. autoattribute:: method
        .. autoattribute:: scheme
        .. autoattribute:: host
        .. autoattribute:: port
        .. autoattribute:: path
        .. autoattribute:: http_version
        .. autoattribute:: headers
        .. autoattribute:: content
        .. autoattribute:: timestamp_start
        .. autoattribute:: timestamp_end
        .. rubric:: Computed Properties and Convenience Methods
        .. autoattribute:: text
        .. autoattribute:: url
        .. autoattribute:: pretty_host
        .. autoattribute:: pretty_url
        .. autoattribute:: query
        .. autoattribute:: cookies
        .. autoattribute:: path_components
        .. automethod:: anticache
        .. automethod:: anticomp
        .. automethod:: constrain_encoding
        .. autoattribute:: urlencoded_form
        .. autoattribute:: multipart_form

    .. autoclass:: Response

        .. rubric:: Data
        .. autoattribute:: http_version
        .. autoattribute:: status_code
        .. autoattribute:: reason
        .. autoattribute:: headers
        .. autoattribute:: content
        .. autoattribute:: timestamp_start
        .. autoattribute:: timestamp_end
        .. rubric:: Computed Properties and Convenience Methods
        .. autoattribute:: text
        .. autoattribute:: cookies

    .. autoclass:: Headers
        :members:
        :special-members:
        :no-undoc-members:

    .. autoclass:: decoded

.. automodule:: mitmproxy.models
    :show-inheritance:
    :members: HTTPFlow, Error, ClientConnection, ServerConnection