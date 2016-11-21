## Complex Examples

| Filename                 | Description                                                                                   |
|:-------------------------|:----------------------------------------------------------------------------------------------|
| change_upstream_proxy.py | Dynamically change the upstream proxy.                                                        |
| dns_spoofing.py          | Use mitmproxy in a DNS spoofing scenario.                                                     |
| dup_and_replay.py        | Duplicates each request, changes it, and then replays the modified request.                   |
| flowbasic.py             | Basic use of mitmproxy's FlowMaster directly.                                                 |
| full_transparency_shim.c | Setuid wrapper that can be used to run mitmproxy in full transparency mode, as a normal user. |
| har_dump.py              | Dump flows as HAR files.                                                                      |
| mitmproxywrapper.py      | Bracket mitmproxy run with proxy enable/disable on OS X                                       |
| nonblocking.py           | Demonstrate parallel processing with a blocking script                                        |
| remote_debug.py          | This script enables remote debugging of the mitmproxy _UI_ with PyCharm.                      |
| sslstrip.py              | sslstrip-like funtionality implemented with mitmproxy                                         |
| stickycookies            | An advanced example of using mitmproxy's FlowMaster directly.                                 |
| stream                   | Enable streaming for all responses.                                                           |
| stream_modify.py         | Modify a streamed response body.                                                              |
| tcp_message.py           | Modify a raw TCP connection                                                                   |
| tls_passthrough.py       | Use conditional TLS interception based on a user-defined strategy.                            |