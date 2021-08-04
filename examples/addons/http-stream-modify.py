"""
Modify a streamed response.

Generally speaking, we recommend *not* to stream messages you need to modify.
Modifying streamed responses is tricky and brittle:
    - If the transfer encoding isn't chunked, you cannot simply change the content length.
    - If you want to replace all occurrences of "foobar", make sure to catch the cases
      where one chunk ends with [...]foo" and the next starts with "bar[...].
"""
from typing import Iterable, Union


def modify(data: bytes) -> Union[bytes, Iterable[bytes]]:
    """
    This function will be called for each chunk of request/response body data that arrives at the proxy,
    and once at the end of the message with an empty bytes argument (b"").

    It may either return bytes or an iterable of bytes (which would result in multiple HTTP/2 data frames).
    """
    return data.replace(b"foo", b"bar")


def responseheaders(flow):
    flow.response.stream = modify
