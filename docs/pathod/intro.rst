.. _intro:

Pathology 101
=============


pathod
------

Pathod is a pathological HTTP daemon designed to let you craft almost any
conceivable HTTP response, including ones that creatively violate the
standards. HTTP responses are specified using a :ref:`small, terse language
<language>` which pathod shares with its evil twin :ref:`pathoc`. To start
playing with pathod, fire up the daemon:

>>> pathod

By default, the service listens on port 9999 of localhost, and the default
crafting anchor point is the path **/p/**. Anything after this URL prefix is
treated as a response specifier. So, hitting the following URL will generate an
HTTP 200 response with 100 bytes of random data:

    http://localhost:9999/p/200:b@100

See the :ref:`language documentation <language>` to get (much) fancier. The
pathod daemon also takes a range of configuration options. To view those, use
the command-line help:

>>> pathod --help

Mimicing a proxy
^^^^^^^^^^^^^^^^

Pathod automatically responds to both straight HTTP and proxy requests. For
proxy requests, the upstream host is ignored, and the path portion of the URL
is used to match anchors. This lets you test software that supports a proxy
configuration by spoofing responses from upstream servers.

By default, we treat all proxy CONNECT requests as HTTPS traffic, serving the
response using either pathod's built-in certificates, or the cert/key pair
specified by the user. You can over-ride this behaviour if you're testing a
client that makes a non-SSL CONNECT request using the **-C** command-line
option.

Anchors
^^^^^^^

Anchors provide an alternative to specifying the response in the URL. Instead,
you attach a response to a pre-configured anchor point, specified with a regex.
When a URL matching the regex is requested, the specified response is served.

>>> pathod -a "/foo=200"

Here, "/foo" is the regex specifying the anchor path, and the part after the "="
is a response specifier.


File Access
^^^^^^^^^^^

There are two operators in the :ref:`language <language>`` that load contents
from file - the **+** operator to load an entire request specification from
file, and the **>** value specifier. In pathod, both of these operators are
restricted to a directory specified at startup, or disabled if no directory is
specified:

>>> pathod -d ~/staticdir"


Internal Error Responses
^^^^^^^^^^^^^^^^^^^^^^^^

Pathod uses the non-standard 800 response code to indicate internal errors, to
distinguish them from crafted responses. For example, a request to:

    http://localhost:9999/p/foo

... will return an 800 response because "foo" is not a valid page specifier.





.. _pathoc:


pathoc
------

Pathoc is a perverse HTTP daemon designed to let you craft almost any
conceivable HTTP request, including ones that creatively violate the standards.
HTTP requests are specified using a :ref:`small, terse language <language>`,
which pathod shares with its server-side twin pathod. To view pathoc's complete
range of options, use the command-line help:

>>> pathoc --help


Getting Started
^^^^^^^^^^^^^^^

The basic pattern for pathoc commands is as follows:

    pathoc hostname request [request ...]

That is, we specify the hostname to connect to, followed by one or more
requests. Lets start with a simple example::

    > pathoc google.com get:/
    07-06-16 12:13:43: >> 'GET':/
    << 302 Found: 261 bytes

Here, we make a GET request to the path / on port 80 of google.com. Pathoc's
output tells us that the server responded with a 302 redirection. We can tell
pathoc to connect using SSL, in which case the default port is changed to 443
(you can over-ride the default port with the **-p** command-line option)::

    > pathoc -s www.google.com get:/
    07-06-16 12:14:56: >> 'GET':/
    << 302 Found: 262 bytes


Multiple Requests
^^^^^^^^^^^^^^^^^

There are two ways to tell pathoc to issue multiple requests. The first is to specify
them on the command-line, like so::

    > pathoc google.com get:/ get:/
    07-06-16 12:21:04: >> 'GET':/
    << 302 Found: 261 bytes
    07-06-16 12:21:04: >> 'GET':/
    << 302 Found: 261 bytes

In this case, pathoc issues the specified requests over the same TCP connection -
so in the above example only one connection is made to google.com

The other way to issue multiple requests is to use the **-n** flag::

    > pathoc -n 2 google.com get:/
    07-06-16 12:21:04: >> 'GET':/
    << 302 Found: 261 bytes
    07-06-16 12:21:04: >> 'GET':/
    << 302 Found: 261 bytes

The output is identical, but two separate TCP connections are made to the
upstream server. These two specification styles can be combined::

    pathoc -n 2 google.com get:/ get:/


Here, two distinct TCP connections are made, with two requests issued over
each.



Basic Fuzzing
^^^^^^^^^^^^^

The combination of pathoc's powerful request specification language and a few
of its command-line options makes for quite a powerful basic fuzzer. Here's an
example::

    pathoc -e -I 200 -t 2 -n 1000 localhost get:/:b@10:ir,@1

The request specified here is a valid GET with a body consisting of 10 random bytes,
but with 1 random byte inserted in a random place. This could be in the headers,
in the initial request line, or in the body itself. There are a few things
to note here:

- Corrupting the request in this way will often make the server enter a state where
  it's awaiting more input from the client. This is where the
  **-t** option comes in, which sets a timeout that causes pathoc to
  disconnect after two seconds.
- The **-n** option tells pathoc to repeat the request 1000 times.
- The **-I** option tells pathoc to ignore HTTP 200 response codes.
  You can use this to fine-tune what pathoc considers to be an exceptional
  condition, and therefore log-worthy.
- The **-e** option tells pathoc to print an explanation of each logged
  request, in the form of an expanded pathoc specification with all random
  portions and automatic header additions resolved. This lets you precisely
  replay a request that triggered an error.


Interacting with Proxies
^^^^^^^^^^^^^^^^^^^^^^^^

Pathoc has a reasonably sophisticated suite of features for interacting with
proxies. The proxy request syntax very closely mirrors that of straight HTTP,
which means that it is possible to make proxy-style requests using pathoc
without any additional syntax, by simply specifying a full URL instead of a
simple path:

>>> pathoc -p 8080 localhost "get:'http://google.com'"

Another common use case is to use an HTTP CONNECT request to probe remote
servers via a proxy. This is done with the **-c** command-line option, which
allows you to specify a remote host and port pair:

>>> pathoc -c google.com:80 -p 8080 localhost get:/

Note that pathoc does **not** negotiate SSL without being explictly instructed
to do so. If you're making a CONNECT request to an SSL-protected resource, you
must also pass the **-s** flag:

>>> pathoc -sc google.com:443 -p 8080 localhost get:/



Embedded response specification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One interesting feature of the Request specification language is that you can
embed a response specification in it, which is then added to the request path.
Here's an example:

>>> pathoc localhost:9999 "get:/p/:s'401:ir,@1'"

This crafts a request that connects to the pathod server, and which then crafts
a response that generates a 401, with one random byte embedded at a random
point. The response specification is parsed and expanded by pathoc, so you see
syntax errors immediately. This really becomes handy when combined with the
**-e** flag to show the expanded request::

    07-06-16 12:32:01: >> 'GET':/p/:s'401:i35,\x27\\x1b\x27:h\x27Content-Length\x27=\x270\x27:h\x27Content-Length\x27=\x270\x27':h'Host'='localhost'
    << 401 Unauthorized: 0 bytes

Note that the embedded response has been resolved *before* being sent to
the server, so that "ir,@1" (embed a random byte at a random location) has
become "i15,\'o\'" (embed the character "o" at offset 15). You now have a
pathoc request specification that is precisely reproducible, even with random
components. This feature comes in terribly handy when testing a proxy, since
you can now drive the server response completely from the client, and have a
complete log of reproducible requests to analyze afterwards.


Request Examples
----------------

.. list-table::
    :widths: 50 50
    :header-rows: 0

    * - get:/
      - Get path /

    * - get:/:b@100
      - 100 random bytes as the body

    * - get:/:h"Etag"="&;drop table browsers;"
      - Add a header

    * - get:/:u"&;drop table browsers;"
      - Add a User-Agent header

    * - get:/:b@100:dr
      - Drop the connection randomly

    * - get:/:b@100,ascii:ir,@1
      - 100 ASCII bytes as the body, and randomly inject a random byte

    * - ws:/
      - Initiate a websocket handshake.


Response Examples
-----------------

.. list-table::
    :widths: 50 50
    :header-rows: 0


    * - 200
      - A basic HTTP 200 response.

    * - 200:r
      - A basic HTTP 200 response with no Content-Length header. This will hang.

    * - 200:da
      - Server-side disconnect after all content has been sent.

    * - 200:b\@100
      - 100 random bytes as the body. A Content-Length header is added, so the disconnect
        is no longer needed.

    * - 200:b\@100:h"Etag"="';drop table servers;"
      - Add a Server header

    * - 200:b\@100:dr
      - Drop the connection randomly

    * - 200:b\@100,ascii:ir,@1
      - 100 ASCII bytes as the body, and randomly inject a random byte

    * - 200:b\@1k:c"text/json"
      - 1k of random bytes, with a text/json content type

    * - 200:b\@1k:p50,120
      - 1k of random bytes, pause for 120 seconds after 50 bytes

    * - 200:b\@1k:pr,f
      - 1k of random bytes, but hang forever at a random location

    * - 200:b\@100:h\@1k,ascii_letters='foo'
      - 100 ASCII bytes as the body, randomly generated 100k header name, with the value
        'foo'.
