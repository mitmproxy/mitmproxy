"""
This inline script modifies a streamed response.
If you do not need streaming, see the modify_response_body example.
Be aware that content replacement isn't trivial:
    - If the transfer encoding isn't chunked, you cannot simply change the content length.
    - If you want to replace all occurences of "foobar", make sure to catch the cases
      where one chunk ends with [...]foo" and the next starts with "bar[...].
"""


def modify(chunks):
    """
    chunks is a generator that can be used to iterate over all chunks.
    Each chunk is a (prefix, content, suffix) tuple.
    For example, in the case of chunked transfer encoding: ("3\r\n","foo","\r\n")
    """
    for prefix, content, suffix in chunks:
        yield prefix, content.replace("foo", "bar"), suffix


def responseheaders(context, flow):
    flow.response.stream = modify
