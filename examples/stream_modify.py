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
