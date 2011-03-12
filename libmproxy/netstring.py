"""
    Netstring is a module for encoding and decoding netstring streams.
    See http://cr.yp.to/proto/netstrings.txt for more information on netstrings.
    Author: Will McGugan (http://www.willmcgugan.com)
"""
from cStringIO import StringIO

    
def header(data):
    return str(len(data))+":"
    
    
class FileEncoder(object):
    def __init__(self, file_out):
        """"
            file_out -- A writable file object
        """
        self.file_out = file_out
        
    def write(self, data):
        """
            Encodes a netstring and writes it to the file object.
            
            data -- A string to be encoded and written
        """  
        write = self.file_out.write
        write(header(data))
        write(data)
        write(',')
        return self
        
    
class DecoderError(Exception):
    PRECEDING_ZERO_IN_SIZE = 0
    MAX_SIZE_REACHED = 1
    ILLEGAL_DIGIT_IN_SIZE = 2
    ILLEGAL_DIGIT = 3
    error_text = {    
        PRECEDING_ZERO_IN_SIZE: "PRECEDING_ZERO_IN_SIZE",
        MAX_SIZE_REACHED: "MAX_SIZE_REACHED",
        ILLEGAL_DIGIT_IN_SIZE: "ILLEGAL_DIGIT_IN_SIZE",
        ILLEGAL_DIGIT: "ILLEGAL_DIGIT"
    }
    def __init__(self, code, text):
        Exception.__init__(self)
        self.code = code
        self.text = text
        
    def __str__(self):
        return "%s (#%i), %s" % (DecoderError.error_text[self.code], self.code, self.text)
        

class Decoder(object):
    """
        A netstring decoder.
        Turns a netstring stream in to a number of discreet strings.    
    """
    def __init__(self, max_size=None):
        """
            Create a netstring-stream decoder object.
            
            max_size -- The maximum size of a netstring encoded string, after which
            a DecoderError will be throw. A value of None (the default) indicates
            that there should be no maximum string size.
        """        
        self.max_size = max_size
        self.data_pos = 0
        self.string_start = 0        
        self.expecting_terminator = False
        self.size_string = ""
        self.data_size = None
        self.remaining_bytes = 0
        self.data_out = StringIO()
        self.yield_data = ""
        
    def feed(self, data):
        """
            A generator that yields 0 or more strings from the given data.
            
            data -- A string containing complete or partial netstring data
        """
        self.data_pos = 0 
        self.string_start = 0        
        while self.data_pos < len(data):        
            if self.expecting_terminator:
                c = data[self.data_pos]                                
                self.data_pos += 1
                if c != ',':
                    raise DecoderError(DecoderError.ILLEGAL_DIGIT, "Illegal digit (%s) at end of data"%repr(c))
                yield self.yield_data
                self.yield_data = ""
                self.expecting_terminator = False
            elif self.data_size is None:
                c = data[self.data_pos]                    
                self.data_pos += 1
                
                if not len(self.size_string):
                    self.string_start = self.data_pos-1                            
                    
                if c in "0123456789":
                    if self.size_string == '0':
                        raise DecoderError(DecoderError.PRECEDING_ZERO_IN_SIZE, "Preceding zeros in size field illegal")                    
                    self.size_string += c                                            
                    if self.max_size is not None and int(self.size_string) > self.max_size:
                        raise DecoderError(DecoderError.MAX_SIZE_REACHED, "Maximum size of netstring exceeded")
                                                
                elif c == ":":        
                    if not len(self.size_string):
                        raise DecoderError(DecoderError.ILLEGAL_DIGIT_IN_SIZE, "Illegal digit (%s) in size field"%repr(c))
                    self.data_size = int(self.size_string)                    
                    self.remaining_bytes = self.data_size
                    
                else:
                    raise DecoderError(DecoderError.ILLEGAL_DIGIT_IN_SIZE, "Illegal digit (%s) in size field"%repr(c))
                        
            elif self.data_size is not None:                                
                get_bytes = min(self.remaining_bytes, len(data)-self.data_pos)                
                chunk = data[self.data_pos:self.data_pos+get_bytes] 
                whole_string = len(chunk) == self.data_size
                if not whole_string:
                    self.data_out.write(chunk)
                self.data_pos += get_bytes                
                self.remaining_bytes -= get_bytes
                if self.remaining_bytes == 0:
                    if whole_string:
                        self.yield_data = chunk
                    else:
                        self.yield_data = self.data_out.getvalue()                        
                        self.data_out.reset()
                        self.data_out.truncate()
                    self.data_size = None
                    self.size_string = "" 
                    self.remaining_bytes = 0                    
                    self.expecting_terminator = True                            
        
        
def decode_file(file_in, buffer_size=1024):
    """
        Generates 0 or more strings from a netstring file.
        
        file_in -- A readable file-like object containing netstring data 
        buffer_size -- The number of bytes to attempt to read in each iteration
        (default = 1024).
    """
    decoder = Decoder()
    while True:
        data = file_in.read(buffer_size)        
        if not len(data):
            return
        for s in decoder.feed(data):
            yield s
