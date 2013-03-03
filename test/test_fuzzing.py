import tservers

"""
    A collection of errors turned up by fuzzing. 
"""

class TestFuzzy(tservers.HTTPProxTest):
    def test_idna_err(self):
        req = r'get:"http://localhost:%s":i10,"\xc6"'
        p = self.pathoc()
        assert p.request(req%self.server.port).status_code == 400

