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
    """
    for chunk in chunks:
        yield chunk.replace("foo", "bar")


def responseheaders(context, flow):
    flow.response.stream = modify
