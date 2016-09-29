.. _filters:

Filter expressions
==================

Many commands in :program:`mitmproxy` and :program:`mitmdump` take a filter expression.
Filter expressions consist of the following operators:

.. documentedlist::
    :header: "Expression" "Description"
    :listobject: mitmproxy.flowfilter.help

- Regexes are Python-style
- Regexes can be specified as quoted strings
- Header matching (~h, ~hq, ~hs) is against a string of the form "name: value".
- Strings with no operators are matched against the request URL.
- The default binary operator is &.

Examples
--------

URL containing "google.com":

.. code-block:: none

    google\.com

Requests whose body contains the string "test":

.. code-block:: none

    ~q ~b test

Anything but requests with a text/html content type:

.. code-block:: none

    !(~q & ~t "text/html")
