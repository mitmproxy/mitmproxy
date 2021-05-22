#!/usr/bin/env python3

import subprocess
import time
import urllib
import urllib.request

def main():
    proc = subprocess.Popen(['python3', '-u', '-m', 'http.server', '8070'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    try:
        time.sleep(0.2)
        resp = urllib.request.urlopen('http://localhost:8070')
        assert b'Directory listing' in resp.read()
    finally:
        proc.terminate()
        try:
            outs, _ = proc.communicate(timeout=0.2)
            print('== subprocess exited with rc =', proc.returncode)
            print(outs.decode('utf-8'))
        except subprocess.TimeoutExpired:
            print('subprocess did not terminate in time')

if __name__ == "__main__":
    main()