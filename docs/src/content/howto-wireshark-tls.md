---
title: "Wireshark and SSL/TLS"
menu:
    howto:
        weight: 1
---

# Wireshark and SSL/TLS Master Secrets

The SSL/TLS master keys can be logged by mitmproxy so that external programs can
decrypt SSL/TLS connections both from and to the proxy. Recent versions of
Wireshark can use these log files to decrypt packets. See the [Wireshark wiki](https://wiki.wireshark.org/SSL#Using_the_.28Pre.29-Master-Secret) for more information.

Key logging is enabled by setting the environment variable `SSLKEYLOGFILE` so
that it points to a writable text file:

```bash
SSLKEYLOGFILE="$PWD/.mitmproxy/sslkeylogfile.txt" mitmproxy
```

You can also `export` this environment variable to make it persistent for all applications started from your current shell session.

You can specify the key file path in Wireshark via `Edit -> Preferences ->
Protocols -> TLS -> (Pre)-Master-Secret log filename`. If your SSLKEYLOGFILE
does not exist yet, just create an empty text file, so you can select it in
Wireshark (or run mitmproxy to create and collect master secrets).

Note that `SSLKEYLOGFILE` is respected by other programs as well, e.g., Firefox
and Chrome. If this creates any issues, you can use `MITMPROXY_SSLKEYLOGFILE`
instead without affecting other applications.
