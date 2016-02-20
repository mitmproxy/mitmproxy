
mitmproxy
=========

.. note::

    We strongly encourage you to use :ref:`inlinescripts` rather than mitmproxy.
        - Inline Scripts are equally powerful and provide an easier syntax.
        - Most examples are written as inline scripts.
        - Multiple inline scripts can be used together.
        - Inline Scripts can either be executed headless with mitmdump or within the mitmproxy UI.


All of mitmproxy's basic functionality is exposed through the **mitmproxy**
library. The example below shows a simple implementation of the "sticky cookie"
functionality included in the interactive mitmproxy program. Traffic is
monitored for ``Cookie`` and ``Set-Cookie`` headers, and requests are rewritten
to include a previously seen cookie if they don't already have one. In effect,
this lets you log in to a site using your browser, and then make subsequent
requests using a tool like curl, which will then seem to be part of the
authenticated session.


.. literalinclude:: ../../examples/stickycookies
   :caption: examples/stickycookies
   :language: python
