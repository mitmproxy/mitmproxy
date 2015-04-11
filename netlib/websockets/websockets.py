from __future__ import absolute_import

from base64 import b64encode
from hashlib import sha1
from mimetools import Message
from netlib import tcp
from netlib import utils
from StringIO import StringIO
import os
import SocketServer
import struct
import io

# Colleciton of utility functions that implement small portions of the RFC6455 WebSockets Protocol
# Useful for building WebSocket clients and servers. 
#
# Emphassis is on readabilty, simplicity and modularity, not performance or completeness
#
# This is a work in progress and does not yet contain all the utilites need to create fully complient client/servers
#
# Spec: https://tools.ietf.org/html/rfc6455

# The magic sha that websocket servers must know to prove they understand RFC6455
websockets_magic = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

class WebSocketFrameValidationException(Exception):
    pass

class WebSocketsFrame(object):
    """
        Represents one websockets frame.
        Constructor takes human readable forms of the frame components
        from_bytes() is also avaliable.

        WebSockets Frame as defined in RFC6455
       
          0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
         +-+-+-+-+-------+-+-------------+-------------------------------+
         |F|R|R|R| opcode|M| Payload len |    Extended payload length    |
         |I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
         |N|V|V|V|       |S|             |   (if payload len==126/127)   |
         | |1|2|3|       |K|             |                               |
         +-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
         |     Extended payload length continued, if payload len == 127  |
         + - - - - - - - - - - - - - - - +-------------------------------+
         |                               |Masking-key, if MASK set to 1  |
         +-------------------------------+-------------------------------+
         | Masking-key (continued)       |          Payload Data         |
         +-------------------------------- - - - - - - - - - - - - - - - +
         :                     Payload Data continued ...                :
         + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
         |                     Payload Data continued ...                |
         +---------------------------------------------------------------+
    """
    def __init__(
        self,
        fin,                          # decmial integer 1 or 0
        opcode,                       # decmial integer 1 - 4
        mask_bit,                     # decimal integer 1 or 0
        payload_length_code,          # decimal integer 1 - 127
        decoded_payload,              # bytestring
        rsv1                  = 0,    # decimal integer 1 or 0
        rsv2                  = 0,    # decimal integer 1 or 0
        rsv3                  = 0,    # decimal integer 1 or 0
        payload               = None, # bytestring 
        masking_key           = None, # 32 bit byte string
        actual_payload_length = None, # any decimal integer
    ):
        self.fin                   = fin
        self.rsv1                  = rsv1
        self.rsv2                  = rsv2
        self.rsv3                  = rsv3
        self.opcode                = opcode
        self.mask_bit              = mask_bit
        self.payload_length_code   = payload_length_code
        self.masking_key           = masking_key
        self.payload               = payload
        self.decoded_payload       = decoded_payload
        self.actual_payload_length = actual_payload_length

    @classmethod
    def from_bytes(cls, bytestring):
        """
          Construct a websocket frame from an in-memory bytestring
          to construct a frame from a stream of bytes, use from_byte_stream() directly
        """ 
        self.from_byte_stream(io.BytesIO(bytestring).read)


    @classmethod
    def default(cls, message, from_client = False):
        """
          Construct a basic websocket frame from some default values. 
          Creates a non-fragmented text frame.
        """ 
        length_code, actual_length = get_payload_length_pair(message)

        if from_client:
            mask_bit    = 1
            masking_key = random_masking_key()
            payload     = apply_mask(message, masking_key)
        else:
            mask_bit    = 0
            masking_key = None
            payload     = message
        
        return cls(
            fin                   = 1, # final frame
            opcode                = 1, # text
            mask_bit              = mask_bit,
            payload_length_code   = length_code,
            payload               = payload,
            masking_key           = masking_key,
            decoded_payload       = message,
            actual_payload_length = actual_length
        )

    def frame_is_valid(self):
        """
         Validate websocket frame invariants, call at anytime to ensure the WebSocketsFrame
         has not been corrupted.
        """ 
        try: 
            assert 0 <= self.fin <= 1
            assert 0 <= self.rsv1 <= 1
            assert 0 <= self.rsv2 <= 1
            assert 0 <= self.rsv3 <= 1
            assert 1 <= self.opcode <= 4
            assert 0 <= self.mask_bit <= 1
            assert 1 <= self.payload_length_code <= 127
            
            if self.mask_bit == 1:
                assert 1 <= len(self.masking_key) <= 4
            else:
                assert self.masking_key == None
            
            assert self.actual_payload_length == len(self.payload)

            if self.payload is not None and self.masking_key is not None:
                assert apply_mask(self.payload, self.masking_key) == self.decoded_payload

            return True 
        except AssertionError:
            return False

    def human_readable(self):
        return "\n".join([
          ("fin                   - " + str(self.fin)),
          ("rsv1                  - " + str(self.rsv1)),
          ("rsv2                  - " + str(self.rsv2)),
          ("rsv3                  - " + str(self.rsv3)),
          ("opcode                - " + str(self.opcode)),
          ("mask_bit              - " + str(self.mask_bit)),
          ("payload_length_code   - " + str(self.payload_length_code)),
          ("masking_key           - " + str(self.masking_key)),
          ("payload               - " + str(self.payload)),
          ("decoded_payload       - " + str(self.decoded_payload)),
          ("actual_payload_length - " + str(self.actual_payload_length)),
          ("use_validation        - " + str(self.use_validation))])

    def safe_to_bytes(self):
      try:
          assert self.frame_is_valid()
          return self.to_bytes()
      except:
          raise WebSocketFrameValidationException()

    def to_bytes(self):
        """
          Serialize the frame back into the wire format, returns a bytestring
          If you haven't checked is_valid_frame() then there's no guarentees that the
          serialized bytes will be correct. see safe_to_bytes()
        """ 

        max_16_bit_int = (1 << 16)
        max_64_bit_int = (1 << 63)

        # break down of the bit-math used to construct the first byte from the frame's integer values
        # first shift the significant bit into the correct position  
        # 00000001 << 7 = 10000000
        # ...
        # then combine:
        # 
        # 10000000 fin
        # 01000000 res1
        # 00100000 res2
        # 00010000 res3
        # 00000001 opcode
        # -------- OR 
        # 11110001   = first_byte

        first_byte  = (self.fin << 7) | (self.rsv1 << 6) | (self.rsv2 << 4) | (self.rsv3 << 4) | self.opcode
        
        second_byte = (self.mask_bit << 7) | self.payload_length_code

        bytes = chr(first_byte) + chr(second_byte)

        if self.actual_payload_length < 126:
            pass
        
        elif self.actual_payload_length < max_16_bit_int:

            # '!H' pack as 16 bit unsigned short
            bytes += struct.pack('!H', self.actual_payload_length) # add 2 byte extended payload length
        
        elif self.actual_payload_length < max_64_bit_int:
            # '!Q' = pack as 64 bit unsigned long long
            bytes += struct.pack('!Q', self.actual_payload_length) # add 8 bytes extended payload length

        if self.masking_key is not None:
            bytes += self.masking_key

        bytes += self.payload # already will be encoded if neccessary

        return bytes


    @classmethod
    def from_byte_stream(cls, read_bytes):
        """
          read a websockets frame sent by a server or client
      
          read_bytes is a function that can be backed
          by sockets or by any byte reader. So this 
          function may be used to read frames from disk/wire/memory
        """ 
        first_byte  = utils.bytes_to_int(read_bytes(1))
        second_byte = utils.bytes_to_int(read_bytes(1))
        
        fin            = first_byte  >> 7  # grab the left most bit
        opcode         = first_byte  & 15  # grab right most 4 bits by and-ing with 00001111
        mask_bit       = second_byte >> 7  # grab left most bit
        payload_length = second_byte & 127 # grab the next 7 bits

        # payload_lengthy > 125 indicates you need to read more bytes
        # to get the actual payload length
        if payload_length <= 125:
           actual_payload_length = payload_length

        elif payload_length == 126:
           actual_payload_length = utils.bytes_to_int(read_bytes(2))

        elif payload_length == 127: 
           actual_payload_length = utils.bytes_to_int(read_bytes(8))

        # masking key only present if mask bit set
        if mask_bit == 1:
            masking_key = read_bytes(4)
        else:
            masking_key = None
        
        payload = read_bytes(actual_payload_length)
        
        if mask_bit == 1:
            decoded_payload = apply_mask(payload, masking_key)
        else:
            decoded_payload = payload

        return cls(
            fin                   = fin,
            opcode                = opcode,
            mask_bit              = mask_bit,
            payload_length_code   = payload_length,
            payload               = payload,
            masking_key           = masking_key,
            decoded_payload       = decoded_payload,
            actual_payload_length = actual_payload_length
        )

def apply_mask(message, masking_key):
    """
    Data sent from the server must be masked to prevent malicious clients
    from sending data over the wire in predictable patterns

    This method both encodes and decodes strings with the provided mask

    Servers do not have to mask data they send to the client.
    https://tools.ietf.org/html/rfc6455#section-5.3
    """
    masks = [utils.bytes_to_int(byte) for byte in masking_key]
    result = ""
    for char in message:
        result += chr(ord(char) ^ masks[len(result) % 4])
    return result

def random_masking_key():
    return os.urandom(4)

def create_client_handshake(host, port, key, version, resource):
    """
      WebSockets connections are intiated by the client with a valid HTTP upgrade request
    """
    headers = [
        ('Host', '%s:%s' % (host, port)),
        ('Connection', 'Upgrade'),
        ('Upgrade', 'websocket'),
        ('Sec-WebSocket-Key', key),
        ('Sec-WebSocket-Version', version)
    ]
    request = "GET %s HTTP/1.1" % resource
    return build_handshake(headers, request)


def create_server_handshake(key, magic = websockets_magic):
    """
      The server response is a valid HTTP 101 response. 
    """ 
    digest = b64encode(sha1(key + magic).hexdigest().decode('hex'))
    headers = [
        ('Connection', 'Upgrade'),
        ('Upgrade', 'websocket'),
        ('Sec-WebSocket-Accept', digest)
    ]
    request = "HTTP/1.1 101 Switching Protocols"
    return build_handshake(headers, request)


def build_handshake(headers, request):
    handshake = [request.encode('utf-8')]
    for header, value in headers:
        handshake.append(("%s: %s" % (header, value)).encode('utf-8'))
    handshake.append(b'\r\n')
    return b'\r\n'.join(handshake)


def read_handshake(read_bytes, num_bytes_per_read):
    """
      From provided function that reads bytes, read in a 
      complete HTTP request, which terminates with a CLRF
    """ 
    response   = b''
    doubleCLRF = b'\r\n\r\n'
    while True:
        bytes = read_bytes(num_bytes_per_read)
        if not bytes:
            break
        response += bytes
        if doubleCLRF in response:
            break
    return response

def get_payload_length_pair(payload_bytestring):
    """
     A websockets frame contains an initial length_code, and an optional
     extended length code to represent the actual length if length code is larger
     than 125
    """ 
    actual_length = len(payload_bytestring)
  
    if actual_length <= 125:
        length_code = actual_length
    elif actual_length >= 126 and actual_length <= 65535:
        length_code = 126
    else:
        length_code = 127
    return (length_code, actual_length)

def server_process_handshake(handshake):
    headers = Message(StringIO(handshake.split('\r\n', 1)[1]))
    if headers.get("Upgrade", None) != "websocket":
        return
    key = headers['Sec-WebSocket-Key']
    return key

def generate_client_nounce():
    return b64encode(os.urandom(16)).decode('utf-8')

