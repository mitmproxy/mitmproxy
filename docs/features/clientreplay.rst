.. _clientreplay:

Client-side replay
==================

Client-side replay does what it says on the tin: you provide a previously saved
HTTP conversation, and mitmproxy replays the client requests one by one. Note
that mitmproxy serializes the requests, waiting for a response from the server
before starting the next request. This might differ from the recorded
conversation, where requests may have been made concurrently.

You may want to use client-side replay in conjunction with the
:ref:`anticache` option, to make sure the server responds with complete data.

================== =================
command-line       :option:`-c path`
mitmproxy shortcut :kbd:`c`
================== =================
