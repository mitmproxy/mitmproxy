"""
This inline script won't work with --stream SIZE command line option.

That's because flow.response.stream will be overwritten to True if the
command line option exists.
"""

def modify(chunks):
    """
    chunks is a generator that can be used to iterate over all chunks.
    Each chunk is a (prefix, content, suffix) tuple. 
    For example, in the case of chunked transfer encoding: ("3\r\n","foo","\r\n")
    """
    for prefix, content, suffix in chunks:
        yield prefix, content.replace("foo","bar"), suffix

def responseheaders(ctx, flow):
    flow.response.stream = modify
    flow.response.stream_large_bodies = 1024 # = 1KB
