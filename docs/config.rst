.. _config:

Configuration
=============

Mitmproxy is configured through a set of files in the users ~/.mitmproxy
directory.

mitmproxy.conf
    Settings for the :program:`mitmproxy`. This file can contain any options supported by
    mitmproxy.

mitmdump.conf
    Settings for the :program:`mitmdump`. This file can contain any options supported by mitmdump.

common.conf
    Settings shared between all command-line tools. Settings in this file are over-ridden by those
    in the tool-specific files. Only options shared by mitmproxy and mitmdump should be used in
    this file.

Syntax
------

Comments
^^^^^^^^

.. code-block:: none

    # this is a comment
    ; this is also a comment (.ini style)
    --- and this is a comment too (yaml style)

Key/Value pairs
^^^^^^^^^^^^^^^

- Keys and values are case-sensitive
- Whitespace is ignored
- Lists are comma-delimited, and enclosed in square brackets

.. code-block:: none

    name = value   # (.ini style)
    name: value    # (yaml style)
    --name value   # (command-line option style)

    fruit = [apple, orange, lemon]
    indexes = [1, 12, 35 , 40]

Flags
^^^^^

These are boolean options that take no value but true/false.

.. code-block:: none

    name = true    # (.ini style)
    name
    --name 	 	   # (command-line option style)

Options
-------

The options available in the config files are precisely those available as
command-line flags, with the key being the option's long name. To get a
complete list of these, use the :option:`--help` option on each of the tools. Be
careful to only specify common options in the **common.conf** file -
unsupported options in this file will be detected as an error on startup.

Examples
--------

common.conf
^^^^^^^^^^^

Note that :option:`--port` is an option supported by all tools.

.. code-block:: none

    port = 8080

mitmproxy.conf
^^^^^^^^^^^^^^

.. code-block:: none

    palette = light
