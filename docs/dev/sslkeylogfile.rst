.. _sslkeylogfile:

TLS Master Secrets
==================

The SSL master keys can be logged by mitmproxy so that external programs can decrypt TLS
connections both from and to the proxy. Key logging is enabled by setting the environment variable
:envvar:`SSLKEYLOGFILE` so that it points to a writable text file.
Recent versions of WireShark can use these log files to decrypt packets.
You can specify the key file path in WireShark via

:samp:`Edit -> Preferences -> Protocols -> SSL -> (Pre)-Master-Secret log filename`.

Note that :envvar:`SSLKEYLOGFILE` is respected by other programs as well, e.g. Firefox and Chrome.
If this creates any issues, you can set :envvar:`MITMPROXY_SSLKEYLOGFILE` alternatively.
