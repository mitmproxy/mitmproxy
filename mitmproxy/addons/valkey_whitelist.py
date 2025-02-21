# include <AMDG.h>
"""
Usage:
$ mitmdump -s valkey_whitelist.py --set whitelist_fp="<file path to whitelist.txt>"
"""

from typing import Optional
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import http
import valkey

default_ip = "127.0.0.1"
# import socket
# default_ip = socket.gethostname() # TODO: ASK SAM
default_port = 6379 # Default port for a valkey server

WHITELIST_403 = b"""<div class="lock"></div>
<div class="message">
  <h1>Access to this page is restricted</h1>
  <p>Please check with the site admin if you believe this is a mistake.</p>
</div>
"""

class Valkey:
    def __init__(self) -> None:
        self.valkey_port: int = default_port
        self.valkey_address: str = default_ip

    def load(self, loader):
        loader.add_option(
            name="valkey_address",
            typespec=str,
            default=default_ip,
            help="The IPv4 address of the Valkey server to be connected"
        )
        loader.add_option(
            name="valkey_port",
            typespec=int,
            default=default_port,
            help="The port of the Valkey server to be connected"
        )
        loader.add_option(
            name="whitelist_fp",
            typespec=Optional[str],
            default=None,
            help="The filepath to whitelist.txt"
        )

    def configure(self, updates):
        if "valkey_address" in updates:
            self.valkey_address = ctx.options.valkey_address

        if "valkey_port" in updates:
            p = ctx.options.valkey_port
            if p < 0 or p > 65535:
                raise exceptions.OptionsError("Port is out of range")
            self.valkey_port = p

        try: # launching valkey server
            v = valkey.Valkey(host=self.valkey_address, port=self.valkey_port, db=0) # db=0: database #0
            if (v.ping() is True):
                print(f"Valkey server is online @ IP {self.valkey_address} & port {self.valkey_port}")
            else:
                raise exceptions.OptionsError("Valkey server was initialized but failed to ping back")
        except:
            raise exceptions.OptionsError("Valkey server configuration failed")

        if "whitelist_fp" in updates:
            fp = ctx.options.whitelist_fp
            if fp is not None:
                with open(fp, 'r') as f:
                    # f = open(fp)
                    # File is now open. Delete all keys from the old db
                    v.flushall() #TODO: This is not a great way of doing things
                    # Pipe contents as fast as possible into valkey
                    pipe = v.pipeline()
                    for line in f:
                        domain = line.strip()
                        pipe.sadd("whitelist", domain) # add domain to the set called whitelist
                    pipe.execute() # run all buffered commands

    def request(self, flow: http.HTTPFlow):
        v = valkey.Valkey(host=self.valkey_address, port=self.valkey_port, db=0)
        if flow.response or flow.error or not flow.live:
            return
        domain = flow.request.pretty_host
        if domain.startswith("www."):
            domain = domain[4:]
        print(f"Checking domain {domain}")
        if not v.sismember("whitelist", domain):
            print(f"Domain {domain} was not found in the whitelist...")
            # flow.response = http.Response.make(
            #     403,
            #     b"Blocked! Go pray! :P\n",
            #     {"Content-Type": "text/plain"}
            # )
            flow.response = http.Response.make(
                403,
                WHITELIST_403,
                {"Content-Type": "text/html; charset=utf-8"}
            )
        else:
            print(f"Domain {domain} was found in the whitelist!") 

addons = [Valkey()] # is this line necessary?