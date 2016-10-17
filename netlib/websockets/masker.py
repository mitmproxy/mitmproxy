class Masker:
    """
    Data sent from the server must be masked to prevent malicious clients
    from sending data over the wire in predictable patterns.

    Servers do not have to mask data they send to the client.
    https://tools.ietf.org/html/rfc6455#section-5.3
    """

    def __init__(self, key):
        self.key = key
        self.offset = 0

    def mask(self, offset, data):
        result = bytearray(data)
        for i in range(len(data)):
            result[i] ^= self.key[offset % 4]
            offset += 1
        result = bytes(result)
        return result

    def __call__(self, data):
        ret = self.mask(self.offset, data)
        self.offset += len(ret)
        return ret
