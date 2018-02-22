---
title: "Features"
menu: "overview"
menu:
    overview:
        weight: 4
---

# Mitmproxy Core Features


- [Anticache](#anticache)
- [Client-side replay](#client-side-replay)
- [Proxy Authentication](#proxy-authentication)
- [Replacements](#replacements)
- [Server-side replay](#server-side-replay)
- [Set Headers](#set-headers)
- [Sticky Auth](#sticky-auth)
- [Sticky Cookies](#sticky-cookies)
- [Streaming](#streaming)
- [Upstream Certificates](#upstream-certificates)


## Anticache

When the `anticache` option is set, it removes headers (`if-none-match` and
`if-modified-since`) that might elicit a `304 not modified` response from the
server. This is useful when you want to make sure you capture an HTTP exchange
in its totality. It's also often used during client-side replay, when you want
to make sure the server responds with complete data.


## Client-side replay

Client-side replay does what it says on the tin: you provide a previously saved
HTTP conversation, and mitmproxy replays the client requests one by one. Note
that mitmproxy serialises the requests, waiting for a response from the server
before starting the next request. This might differ from the recorded
conversation, where requests may have been made concurrently.

You may want to use client-side replay in conjunction with the `anticache`
option, to make sure the server responds with complete data.

## Proxy Authentication

Asks the user for authentication before they are permitted to use the proxy.
Authentication headers are stripped from the flows, so they are not passed to
upstream servers. For now, only HTTP Basic authentication is supported. The
proxy auth options are not compatible with the transparent, socks or reverse
proxy mode.


## Replacements

The `replacements` option lets you specify an arbitrary number of patterns that
define text replacements within flows. A replacement pattern looks like this:

{{< highlight none  >}}
/patt/regex/replacement
{{< / highlight >}}

Here, **patt** is a mitmproxy filter expression that defines which flows a
replacement applies to, **regex** is a valid Python regular expression that
defines what gets replaced, and **replacement** is a string literal that is
substituted in. The separator is arbitrary, and defined by the first character.
If the replacement string literal starts with `@`, it is treated as a file path
from which the replacement is read.

Replace hooks fire when either a client request or a server response is
received. Only the matching flow component is affected: so, for example,
if a replace hook is triggered on server response, the replacement is
only run on the Response object leaving the Request intact. You control
whether the hook triggers on the request, response or both using the
filter pattern. If you need finer-grained control than this, it's simple
to create a script using the replacement API on Flow components.

### Examples

Replace `foo` with `bar` in requests:

{{< highlight none  >}}
:~q:foo:bar
{{< / highlight >}}

Replace `foo` with with the data read from `~/xss-exploit`:

{{< highlight bash  >}}
mitmdump --replacements :~q:foo:@~/xss-exploit
{{< / highlight >}}


## Server-side replay

The `server_replay` option lets us replay server responses from saved HTTP
conversations. To do this, we use a set of heuristics to match incoming requests
with saved responses. By default, we exclude request headers when matching
incoming requests with responses from the replay file, and use only the URL and
request method for matching. This works in most circumstances, and makes it
possible to replay server responses in situations where request headers would
naturally vary, e.g. using a different user agent.

There is a slew of ways to customise the matching heuristic, including
specifying headers to include, request parameters to exclude, etc. These options
are collected under the `server_replay` prefix - please see the built-in
documentation for details.

### Response refreshing

Simply replaying server responses without modification will often result in
unexpected behaviour. For example cookie timeouts that were in the future at the
time a conversation was recorded might be in the past at the time it is
replayed. By default, mitmproxy refreshes server responses before sending them
to the client. The **date**, **expires** and **last-modified** headers are all
updated to have the same relative time offset as they had at the time of
recording. So, if they were in the past at the time of recording, they will be
in the past at the time of replay, and vice versa. Cookie expiry times are
updated in a similar way.

You can turn off this behaviour by setting the `server_replay_refresh` option to
`false`.

### Replaying a session recorded in Reverse-proxy Mode

If you have captured the session in reverse proxy mode, in order to replay it
you still have to specify the server URL, otherwise you may get the error: 'HTTP
protocol error in client request: Invalid HTTP request form (expected authority
or absolute...)'.

During replay, when the client's requests match previously recorded requests,
then the respective recorded responses are simply replayed by mitmproxy.
Otherwise, the unmatched requests is forwarded to the upstream server. If
forwarding is not desired, you can use the --kill (-k) switch to prevent that.

## Set Headers

The `setheaders` option lets you specify a set of headers to be added to
requests or responses, based on a filter pattern. A `setheaders` expression
looks like this:

{{< highlight none  >}}
/patt/name/value
{{< / highlight >}}

Here, **patt** is a mitmproxy filter expression that defines which flows to set
headers on, and **name** and **value** are the header name and the value to set
respectively.

## Sticky auth

The `stickyauth` option is analogous to the sticky cookie option, in that HTTP
**Authorization** headers are simply replayed to the server once they have been
seen. This is enough to allow you to access a server resource using HTTP Basic
authentication through the proxy. Note that <span
data-role="program">mitmproxy</span> doesn't (yet) support replay of HTTP Digest
authentication.

## Sticky cookies

When the `stickycookie` option is set, **mitmproxy** will add the cookie most
recently set by the server to any cookie-less request. Consider a service that
sets a cookie to track the session after authentication. Using sticky cookies,
you can fire up mitmproxy, and authenticate to a service as you usually would
using a browser. After authentication, you can request authenticated resources
through mitmproxy as if they were unauthenticated, because mitmproxy will
automatically add the session tracking cookie to requests. Among other things,
this lets you script interactions with authenticated resources (using tools like
wget or curl) without having to worry about authentication.

Sticky cookies are especially powerful when used in conjunction with [client
replay]({{< relref "#client-side-replay" >}}) - you can record the
authentication process once, and simply replay it on startup every time you need
to interact with the secured resources.

## Streaming

By default, mitmproxy will read an entire request/response, perform any
indicated manipulations on it, and then send the message on to the other party.
This can be problematic when downloading or uploading large files. When
streaming is enabled, message bodies are not buffered on the proxy but instead
sent directly to the server/client. HTTP headers are still fully buffered before
being sent.

Request/response streaming is enabled by specifying a size cutoff in the
`stream_large_bodies` option.

### Customizing Streaming

You can also use a script to customise exactly which requests or responses are
streamed. Requests/Responses that should be tagged for streaming by setting
their ``.stream`` attribute to ``True``:

{{< example src="examples/complex/stream.py" lang="py" >}}


### Websockets

The `stream_websockets` option enables an analogous behaviour for websockets.
When WebSocket streaming is enabled, portions of the code which may perform
changes to the WebSocket message payloads will not have any effect on the actual
payload sent to the server as the frames are immediately forwarded to the
server. In contrast to HTTP streaming, where the body is not stored, the message
payload will still be stored in the WebSocket flow.

## Upstream Certificates

When mitmproxy receives a connection destined for an SSL-protected service, it
freezes the connection before reading its request data, and makes a connection
to the upstream server to "sniff" the contents of its SSL certificate. The
information gained - the **Common Name** and **Subject Alternative Names** - is
then used to generate the interception certificate, which is sent to the client
so the connection can continue.

This rather intricate little dance lets us seamlessly generate correct
certificates even if the client has specified only an IP address rather than the
hostname. It also means that we don't need to sniff additional data to generate
certs in transparent mode.

Upstream cert sniffing is on by default, and can optionally be turned off with
the `upstream_cert` option.