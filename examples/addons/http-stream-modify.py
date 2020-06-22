"""
Modify a streamed response.

Generally speaking, we recommend *not* to stream messages you need to modify.
Modifying streamed responses is tricky and brittle:
    - If the transfer encoding isn't chunked, you cannot simply change the content length.
    - If you want to replace all occurrences of "foobar", make sure to catch the cases
      where one chunk ends with [...]foo" and the next starts with "bar[...].
"""


def modify(chunks):
    """
    chunks is a generator that can be used to iterate over all chunks.
    """
    for chunk in chunks:
        yield chunk.replace("foo", "bar")


def responseheaders(flow):
    flow.response.stream = modify
