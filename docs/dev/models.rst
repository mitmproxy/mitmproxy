.. _models:

Datastructures
==============

.. automodule:: mitmproxy.models
    :members: HTTPFlow, HTTPRequest, HTTPResponse


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

        .. automethod:: make

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

.. automodule:: netlib.multidict

    .. autoclass:: MultiDictView

        .. automethod:: get_all
        .. automethod:: set_all
        .. automethod:: add
        .. automethod:: insert
        .. automethod:: keys
        .. automethod:: values
        .. automethod:: items
        .. automethod:: to_dict

.. autoclass:: mitmproxy.models.Error
    :show-inheritance:

.. autoclass:: mitmproxy.models.ServerConnection
    :show-inheritance:

.. autoclass:: mitmproxy.models.ClientConnection
    :show-inheritance: