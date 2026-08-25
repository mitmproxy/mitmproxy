---
title: "Features"
weight: 4
aliases:
  - /overview-features/
---

# Features

- [Anticache](#anticache)
- [Blocklist](#blocklist)
- [Client-side replay](#client-side-replay)
- [Map Local](#map-local)
- [Map Remote](#map-remote)
- [Modify Body](#modify-body)
- [Modify Headers](#modify-headers)
- [Proxy Authentication](#proxy-authentication)
- [Server-side replay](#server-side-replay)
- [Sticky Auth](#sticky-auth)
- [Sticky Cookies](#sticky-cookies)
- [Streaming](#streaming)

## Anticache

When the `anticache` option is set, it removes headers (`if-none-match` and
`if-modified-since`) that might elicit a `304 Not Modified` response from the
server. This is useful when you want to make sure you capture an HTTP exchange
in its totality. It's also often used during client-side replay, when you want
to make sure the server responds with complete data.

## Blocklist

Using the `block_list` option, you can block particular websites or requests.
Mitmproxy returns a fixed HTTP status code instead, or no response at all.

`block_list` patterns look like this:

```
/flow-filter/status-code
```

* **flow-filter** is an optional mitmproxy [filter expression]({{< relref "/concepts/filters">}})
  that describes which requests should be blocked.
* **status-code** is the [HTTP status code](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes)
  served by mitmproxy for blocked requests.
  A special status code of 444 instructs mitmproxy to "hang up" and not send any response at all.

The _separator_ is arbitrary, and is defined by the first character.

#### Examples

Pattern | Description
------- | -----------
`:~d google-analytics.com:404` | Block all requests to google-analytics.com, and return a "404 Not Found" instead.
`:~d example.com$:444` | Block all requests to example.com, and do not send an HTTP response.
`:!~d ^example\.com$:403` | Only allow HTTP requests to *example.com*. Note that this is not secure against an active adversary and can be bypassed, for example by switching to non-HTTP protocols.

## Client-side replay

Client-side replay does what it says on the tin: you provide a previously saved
HTTP conversation, and mitmproxy replays the client requests one by one. Note
that mitmproxy serialises the requests, waiting for a response from the server
before starting the next request. This might differ from the recorded
conversation, where requests may have been made concurrently.

You may want to use client-side replay in conjunction with the `anticache`
option, to make sure the server responds with complete data.

## Map Local

The `map_local` option lets you specify an arbitrary number of patterns that
define redirections of HTTP requests to local files or directories.
The local file is fetched instead of the original resource
and transparently returned to the client.

`map_local` patterns look like this:

```
|url-regex|local-path
|flow-filter|url-regex|local-path
```

* **local-path** is the file or directory that should be served to the client.

* **url-regex** is a regular expression applied on the request URL. It must match for a redirect to take place.

* **flow-filter** is an optional mitmproxy [filter expression]({{< relref "/concepts/filters">}})
that additionally constrains which requests will be redirected.

The _separator_ is arbitrary, and is defined by the first character (`|` in the example above).


#### Examples

Pattern | Description
------- | -----------
`\|example.com/main.js\|~/main-local.js` | Replace `example.com/main.js` with `~/main-local.js`.
`\|example.com/static\|~/static` | Replace `example.com/static/foo/bar.css` with `~/static/foo/bar.css`.
`\|example.com/static/foo\|~/static` | Replace `example.com/static/foo/bar.css` with `~/static/bar.css`.
`\|~m GET\|example.com/static\|~/static` | Replace `example.com/static/foo/bar.css` with `~/static/foo/bar.css` (but only for GET requests).

### Details

If *local-path* is a file, this file will always be served. File changes will be reflected immediately, there is no caching.

If *local-path* is a directory, *url-regex* is used to split the request URL in two parts and part on the right is appended to *local-path*, excluding the query string.
However, if *url-regex* contains a regex capturing group, this behavior changes and the first capturing group is appended instead (and query strings are not stripped).
Special characters are mapped to `_`. If the file cannot be found, `/index.html` is appended and we try again. Directory traversal outside of the originally specified directory is not possible.

To illustrate this, consider the following example which maps all requests for `example.org/css*` to the local directory `~/static-css`.

<pre>
                  ┌── url regex ──┬─ local path ─┐
map_local option: |<span style="color:#f92672">example.com/css</span>|<span style="color:#82b719">~/static-css</span>
                   <!--                     -->         │
                   <!--                     -->         │    URL is split here
                   <!--                     -->         ▼            ▼
HTTP Request URL: https://<span style="color:#f92672">example.com/css</span><span style="color:#66d9ef">/print/main.css</span><span style="color:#bbb">?timestamp=123</span>
                          <!--                     -->               <!--                            -->      │        <!--                         -->        ▼
                          <!--                     -->               <!--                            -->      ▼        <!--                         -->      query string is ignored
Served File:      Preferred: <span style="color:#82b719">~/static-css</span><span style="color:#66d9ef">/print/main.css</span>
                   Fallback: <span style="color:#82b719">~/static-css</span><span style="color:#66d9ef">/print/main.css</span>/index.html
                  Otherwise: 404 response without content
</pre>

If the file depends on the query string, we can use regex capturing groups. In this example, all `GET` requests for
`example.org/index.php?page=<page-name>` are mapped to `~/static-dir/<page-name>`:

<pre>
                    flow
                  ┌filter┬─────────── url regex ───────────┬─ local path ─┐
map_local option: |~m GET|<span style="color:#f92672">example.com/index.php\\?page=</span><span style="color:#66d9ef">(.+)</span>|<span style="color:#82b719">~/static-dir</span>
                          <!--                     -->  │                          <!--                            --> │
                          <!--                     -->  │                          <!--                            --> │ regex group = suffix
                          <!--                     -->  ▼                          <!--                            --> ▼
HTTP Request URL: https://<span style="color:#f92672">example.com/index.php?page=</span><span style="color:#66d9ef">aboutus</span></span>
                          <!--                     -->                           <!--                            -->   │
                          <!--                     -->                           <!--                            -->   ▼
Served File:                 Preferred: <span style="color:#82b719">~/static-dir</span>/<span style="color:#66d9ef">aboutus</span>
                              Fallback: <span style="color:#82b719">~/static-dir</span>/<span style="color:#66d9ef">aboutus</span>/index.html
                             Otherwise: 404 response without content
</pre>

## Map Remote

The `map_remote` option lets you specify an arbitrary number of patterns that
define replacements within HTTP request URLs before they are sent to a server.
The substituted URL is fetched instead of the original resource
and the corresponding HTTP response is returned transparently to the client.
`map_remote` patterns look like this:

```
|flow-filter|url-regex|replacement
|url-regex|replacement
```

* **flow-filter** is an optional mitmproxy [filter expression]({{< relref "/concepts/filters">}})
that defines which requests the `map_remote` option applies to.

* **url-regex** is a valid Python regular expression that defines what gets replaced in the URLs of requests.

* **replacement** is a string literal that is substituted in.

The _separator_ is arbitrary, and is defined by the first character (`|` in the example above).

#### Examples

Map all requests ending with `.jpg` to `https://placedog.net/640/480?random`.

```
|.*\.jpg$|https://placedog.net/640/480?random
```

Re-route all GET requests from `example.org` to `mitmproxy.org` (using `|` as the separator):

```
|~m GET|//example.org/|//mitmproxy.org/
```

## Modify Body

The `modify_body` option lets you specify an arbitrary number of patterns that
define replacements within bodies of flows. `modify_body` patterns look like this:

```
/flow-filter/body-regex/replacement
/flow-filter/body-regex/@file-path
/body-regex/replacement
/body-regex/@file-path
```

* **flow-filter** is an optional mitmproxy [filter expression]({{< relref "/concepts/filters">}})
that defines which flows a replacement applies to.

* **body-regex** is a valid Python regular expression that defines what gets replaced.

* **replacement** is a string literal that is substituted in. If the replacement string
literal starts with `@` as in `@file-path`, it is treated as a **file path** from which the replacement is read.

The _separator_ is arbitrary, and is defined by the first character (`/` in the example above).

Modify hooks fire when either a client request or a server response is
received. Only the matching flow component is affected: so, for example,
if a modify hook is triggered on server response, the replacement is
only run on the Response object leaving the Request intact. You control
whether the hook triggers on the request, response or both using the
filter pattern. If you need finer-grained control than this, it's simple
to create a script using the replacement API on Flow components. Body
modifications have no effect on streamed bodies. See
[Streaming]({{< relref "#streaming" >}}) for more detail.

#### Examples

Replace `foo` with `bar` in bodies of requests:

```
/~q/foo/bar
```

Replace `foo` with the data read from `~/xss-exploit`:

```bash
mitmdump --modify-body :~q:foo:@~/xss-exploit
```

## Modify Headers

The `modify_headers` option lets you specify a set of headers to be modified.
New headers can be added, and existing headers can be overwritten or removed.
`modify_headers` patterns look like this:

```
/flow-filter/name/value
/flow-filter/name/@file-path
/name/value
/name/@file-path
```

* **flow-filter** is an optional mitmproxy [filter expression]({{< relref "/concepts/filters">}})
that defines which flows to modify headers on.

* **name** is the header name to be set, replaced or removed.

* **value** is the header value to be set or replaced. An empty **value** removes existing
headers with **name**. If the value string literal starts with `@` as in
`@file-path`, it is treated as a **file path** from which the replacement is read.

The _separator_ is arbitrary, and is defined by the first character (`/` in the example above).

Existing headers are overwritten by default. This can be changed using a filter expression.

Modify hooks fire when either a client request or a server response is
received. Only the matching flow component is affected: so, for example,
if a modify hook is triggered on server response, the replacement is
only run on the Response object leaving the Request intact. You control
whether the hook triggers on the request, response or both using the
filter pattern. If you need finer-grained control than this, it's simple
to create a script using the replacement API on Flow components.

#### Examples

Set the `Host` header to `example.org` for all requests (existing `Host`
headers are replaced):

```
/~q/Host/example.org
```

Set the `Host` header to `example.org` for all requests that do not have an
existing `Host` header:

```
/~q & !~h Host:/Host/example.org
```

Set the `User-Agent` header to the data read from `~/useragent.txt` for all requests
(existing `User-Agent` headers are replaced):

```
/~q/User-Agent/@~/useragent.txt
```

Remove existing `Host` headers from all requests:

```
/~q/Host/
```

## Proxy Authentication

The `proxyauth` option asks the user for authentication before they are permitted to use the proxy.
Authentication headers are stripped from the flows, so they are not passed to
upstream servers. For now, only HTTP Basic Authentication is supported.

Proxy Authentication does not work well in transparent proxy mode by design
because the client is not aware that it is talking to a proxy.
Mitmproxy will re-request credentials for every individual domain.
SOCKS proxy authentication is currently unimplemented
([#738](https://github.com/mitmproxy/mitmproxy/issues/738)).

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
sent directly to the server/client. This currently means that the message body
will not be accessible within mitmproxy, and body modifications will have no
effect. HTTP headers are still fully buffered before being sent.

Request/response streaming is enabled by specifying a size cutoff in the
`stream_large_bodies` option.

### Customizing Streaming

You can also use a script to customise exactly which requests or responses are
streamed. Requests/Responses that should be tagged for streaming by setting
their ``.stream`` attribute to ``True``:

{{< example src="examples/addons/http-stream-simple.py" lang="py" >}}
