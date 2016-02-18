.. _serverreplay:

Server-side replay
==================

Server-side replay lets us replay server responses from a saved HTTP
conversation.

Matching requests with responses
--------------------------------

By default, :program:`mitmproxy` excludes request headers when matching incoming
requests with responses from the replay file. This works in most circumstances,
and makes it possible to replay server responses in situations where request
headers would naturally vary, e.g. using a different user agent.
The :option:`--rheader headername` command-line option allows you to override
this behaviour by specifying individual headers that should be included in matching.


Response refreshing
-------------------

Simply replaying server responses without modification will often result in
unexpected behaviour. For example cookie timeouts that were in the future at
the time a conversation was recorded might be in the past at the time it is
replayed. By default, :program:`mitmproxy` refreshes server responses before sending
them to the client. The **date**, **expires** and **last-modified** headers are
all updated to have the same relative time offset as they had at the time of
recording. So, if they were in the past at the time of recording, they will be
in the past at the time of replay, and vice versa. Cookie expiry times are
updated in a similar way.

You can turn off response refreshing using the :option:`--norefresh` argument, or using
the :kbd:`o` options shortcut within :program:`mitmproxy`.

================== =================
command-line       :option:`-S path`
mitmproxy shortcut :kbd:`S`
================== =================
