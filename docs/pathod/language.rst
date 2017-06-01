.. _language:

language spec
=============

************
HTTP Request
************

    **method:path:[colon-separated list of features]**

.. list-table::
    :widths: 20 80
    :header-rows: 0

    * - method
      - A :ref:`VALUE` specifying the HTTP method to
        use. Standard methods do not need to be enclosed in quotes, while
        non-standard methods can be specified as quoted strings.

        The special method **ws** creates a valid websocket upgrade
        GET request, and signals to pathoc to switch to websocket recieve
        mode if the server responds correctly. Apart from that, websocket
        requests are just like any other, and all aspects of the request
        can be over-ridden.
    * - h\ :ref:`VALUE`\ =\ :ref:`VALUE`\
      - Set a header.
    * - r
      - Set the **raw** flag on this response. Pathod will not calculate a
        *Content-Length* header if a body is set.
    * - c\ :ref:`VALUE`
      - A shortcut for setting the Content-Type header. Equivalent to
        ``h"Content-Type"=VALUE``
    * - u\ :ref:`VALUE`
        uSHORTCUT
      - Set a User-Agent header on this request. You can specify either a
        complete :ref:`VALUE`, or a User-Agent shortcut: **android**,
        **blackberry**, **bingbot**, **chrome**, **firefox**, **googlebot**,
        **ie9**, **ipad**, **iphone**, **safari**.
    * - b\ :ref:`VALUE`
      - Set the body. The appropriate Content-Length header is added
        automatically unless the **r** flag is set.
    * - s\ :ref:`VALUE`
      - An embedded Response specification, appended to the path of the request.
    * - x\ :ref:`INTEGER`
      - Repeat this message N times.
    * - d\ :ref:`OFFSET`
      - Disconnect after OFFSET bytes (HTTP/1 only).
    * - i\ :ref:`OFFSET`,\ :ref:`VALUE`
      - Inject the specified value at the offset (HTTP/1 only)
    * - p\ :ref:`OFFSET`,SECONDS
      - Pause for SECONDS seconds after OFFSET bytes. SECONDS can be an integer
        or "f" to pause forever (HTTP/1 only)


*************
HTTP Response
*************

    **code:[colon-separated list of features]**

.. list-table::
    :widths: 20 80
    :header-rows: 0

    * - code
      - An integer specifying the HTTP response code.

        The special method **ws** creates a valid websocket upgrade
        response (code 101), and moves pathod to websocket mode. Apart
        from that, websocket responses are just like any other, and all
        aspects of the response can be over-ridden.
    * - m\ :ref:`VALUE`
      - HTTP Reason message. Automatically chosen according to the response
        code if not specified. (HTTP/1 only)
    * - h\ :ref:`VALUE`\ =\ :ref:`VALUE`\
      - Set a header.
    * - r
      - Set the **raw** flag on this response. Pathod will not calculate a
        *Content-Length* header if a body is set.
    * - l\ :ref:`VALUE`
      - A shortcut for setting the Location header. Equivalent to
        ``h"Location"=VALUE``
    * - c\ :ref:`VALUE`
      - A shortcut for setting the Content-Type header. Equivalent to
        ``h"Content-Type"=VALUE``
    * - b\ :ref:`VALUE`
      - Set the body. The appropriate Content-Length header is added
        automatically unless the **r** flag is set.
    * - d\ :ref:`OFFSET`
      - Disconnect after OFFSET bytes (HTTP/1 only).
    * - i\ :ref:`OFFSET`,\ :ref:`VALUE`
      - Inject the specified value at the offset (HTTP/1 only)
    * - p\ :ref:`OFFSET`,SECONDS
      - Pause for SECONDS seconds after OFFSET bytes. SECONDS can be an integer
        or "f" to pause forever (HTTP/1 only)

***************
Websocket Frame
***************

    **wf:[colon-separated list of features]**

.. list-table::
    :widths: 20 80
    :header-rows: 0

    * - b\ :ref:`VALUE`
      - Set the frame payload. If a masking key is present, the value is
        encoded automatically.
    * - c\ :ref:`INTEGER`
      - Set the op code. This can either be an integer from 0-15, or be one of
        the following opcode names: **text** (the default), **continue**,
        **binary**, **close**, **ping**, **pong**.
    * - d\ :ref:`OFFSET`
      - Disconnect after OFFSET bytes
    * - i\ :ref:`OFFSET`,\ :ref:`VALUE`
      - Inject the specified value at the offset
    * - p\ :ref:`OFFSET`,SECONDS
      - Pause for SECONDS seconds after OFFSET bytes. SECONDS can be an integer
        or "f" to pause forever
    * - x\ :ref:`INTEGER`
      - Repeat this message N times.
    * - [-]fin
      - Set or un-set the **fin** bit.
    * - k\ :ref:`VALUE`
      - Set the masking key. The resulting value must be exactly 4 bytes long.
        The special form **knone** specifies that no key should be set, even if
        the mask bit is on.
    * - l\ :ref:`INTEGER`
      - Set the payload length in the frame header, regardless of the actual
        body length.
    * - [-]mask
      - Set or un-set the <b>mask</b> bit.
    * - r\ :ref:`VALUE`
      - Set the raw frame payload. This disables masking, even if the key is present.
    * - [-]rsv1
      - Set or un-set the **rsv1** bit.
    * - [-]rsv2
      - Set or un-set the **rsv2** bit.
    * - [-]rsv2
      - Set or un-set the **rsv2** bit.



**********
Data types
**********

.. _INTEGER:

INTEGER
^^^^^^^

.. _OFFSET:

OFFSET
^^^^^^

Offsets are calculated relative to the base message, before any injections or
other transforms are applied. They have 3 flavors:

=======                 ==========================
integer                 An integer byte offset
**r**                   A random location
**a**                   The end of the message
=======                 ==========================


.. _VALUE:

VALUE
^^^^^

Literals
""""""""

Literal values are specified as a quoted strings::

    "foo"

Either single or double quotes are accepted, and quotes can be escaped with
backslashes within the string::

    'fo\'o'

Literal values can contain Python-style backslash escape sequences::

    'foo\r\nbar'



Generated
"""""""""

An @-symbol lead-in specifies that generated data should be used. There are two
components to a generator specification - a size, and a data type. By default
pathod assumes a data type of "bytes".

Here's a value specifier for generating 100 bytes::

    @100

You can use standard suffixes to indicate larger values. Here, for instance, is
a specifier for generating 100 megabytes:

    @100m

Data is generated and served efficiently - if you really want to send a
terabyte of data to a client, pathod can do it. The supported suffixes are:

==========          ====================
b                   1024**0 (bytes)
k                   1024**1 (kilobytes)
m                   1024**2 (megabytes)
g                   1024**3 (gigabytes)
t                   1024**4 (terabytes)
==========          ====================

Data types are separated from the size specification by a comma. This specification
generates 100mb of ASCII::

    @100m,ascii

Supported data types are:

=================          ==============================================
ascii                      All ASCII characters
ascii_letters              A-Za-z
ascii_lowercase            a-z
ascii_uppercase            A-Z
bytes                      All 256 byte values
digits                     0-9
hexdigits                  0-f
octdigits                  0-7
punctuation                !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ and space
whitespace                 \\t \\n \\x0b \\x0c \\r and space
=================          ==============================================



Files
"""""

You can load a value from a specified file path. To do so, you have to specify a
_staticdir_ option to pathod on the command-line, like so:

>>> pathod -d ~/myassets

All paths are relative paths under this directory. File loads are indicated by
starting the value specifier with the left angle bracket::

    <my/path

The path value can also be a quoted string, with the same syntax as literals::

    <"my/path"
