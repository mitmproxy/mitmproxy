.. _mitmdump:
.. program:: mitmdump

mitmdump
========


**mitmdump** is the command-line companion to mitmproxy. It provides
tcpdump-like functionality to let you view, record, and programmatically
transform HTTP traffic. See the :option:`--help` flag output for complete
documentation.



Examples
--------

Saving traffic
^^^^^^^^^^^^^^

>>> mitmdump -w outfile

Start up mitmdump in proxy mode, and write all traffic to **outfile**. 


Filtering saved traffic
^^^^^^^^^^^^^^^^^^^^^^^

>>> mitmdump -nr infile -w outfile "~m post"

Start mitmdump without binding to the proxy port (:option:`-n`), read all flows from
infile, apply the specified filter expression (only match POSTs), and write to
outfile.


Client replay
^^^^^^^^^^^^^

>>> mitmdump -nc outfile

Start mitmdump without binding to the proxy port (:option:`-n`), then replay all
requests from outfile (:option:`-c filename`). Flags combine in the obvious way, so
you can replay requests from one file, and write the resulting flows to
another:

>>> mitmdump -nc srcfile -w dstfile

See the :ref:`clientreplay` section for more information.


Running a script
^^^^^^^^^^^^^^^^

>>> mitmdump -s examples/add_header.py

This runs the **add_header.py** example script, which simply adds a new header
to all responses.

Scripted data transformation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

>>> mitmdump -ns examples/add_header.py -r srcfile -w dstfile

This command loads flows from **srcfile**, transforms it according to the
specified script, then writes it back to **dstfile**.

