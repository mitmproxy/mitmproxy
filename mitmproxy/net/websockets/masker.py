import sys


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
        datalen = len(data)
        offset_mod = offset % 4
        data = int.from_bytes(data, sys.byteorder)
        num_keys = (datalen + offset_mod + 3) // 4
        mask = int.from_bytes((self.key * num_keys)[offset_mod:datalen +
                                                    offset_mod], sys.byteorder)
        return (data ^ mask).to_bytes(datalen, sys.byteorder)

    def __call__(self, data):
        ret = self.mask(self.offset, data)
        self.offset += len(ret)
        return ret
