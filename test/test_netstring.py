from libmproxy import netstring
from cStringIO import StringIO
import libpry



class uNetstring(libpry.AutoTree):
    def setUp(self):
        self.test_data = "Netstring module by Will McGugan"
        self.encoded_data = "9:Netstring,6:module,2:by,4:Will,7:McGugan,"

    def test_header(self):
        tests = [ ("netstring", "9:"),
                  ("Will McGugan", "12:"),
                  ("", "0:") ]
        for test, result in tests:
            assert netstring.header(test) == result 
            
    def test_encode(self):
        tests = [ ("netstring", "9:netstring,"),
                  ("Will McGugan", "12:Will McGugan,"),
                  ("", "0:,") ]
        for test, result in tests:                
            assert netstring.encode(test) == result 
            
    def test_file_encoder(self):
        file_out = StringIO()
        data = self.test_data.split()
        encoder = netstring.FileEncoder(file_out)
        for s in data:
            encoder.write(s)
        encoded_data = file_out.getvalue()            
        assert encoded_data == self.encoded_data
        
    def test_decode_file(self):
        data = self.test_data.split()
        for buffer_size in range(1, len(self.encoded_data)):
            file_in = StringIO(self.encoded_data[:])            
            decoded_data = list(netstring.decode_file(file_in, buffer_size = buffer_size))
            assert decoded_data == data
        
    def test_decoder(self):
        encoded_data = self.encoded_data
        for step in range(1, len(encoded_data)):
            i = 0
            chunks = []
            while i < len(encoded_data):
                chunks.append(encoded_data[i:i+step])
                i += step                
            decoder = netstring.Decoder()
            decoded_data = [] 
            for chunk in chunks:
                for s in decoder.feed(chunk):
                    decoded_data.append(s)
            assert decoded_data == self.test_data.split()




tests = [
    uNetstring()
]

