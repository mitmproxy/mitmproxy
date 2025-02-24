# include <AMDG.h>
"""
This is a mitmproxy plugin that enforces a whitelist using a Valkey (Redis) database.
If the user tries to access a website that's not on the whitelist, they'll be 
delivered to a custom 403 page.

The whitelist is loaded into the database from a file called "whitelist.txt" which
contains domains delimited by newlines.

e.g:
    foo.com
    example.com
    cats.com

    
(Example) Usage:
---------------------
$ mitmdump -s valkey_whitelist.py --set whitelist_filepath="<file path to whitelist.txt>"

        
Environment variables:
---------------------
IP: The IPv4 address of the valkey server
PORT: The port the valkey server is listening on
WHITELIST_DIR: The directory containing whitelist.txt
ERRPAGE_DIR: The directory containing 403.html
"""

import os
import hashlib
from typing import Optional
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import http
import valkey


class Valkey:
    def __init__(self) -> None:
        self.valkey_port: int = int(os.environ.get("PORT", "6379"))
        self.valkey_address: str = os.environ.get("IP", "127.0.0.1")

    def load(self, loader):
        loader.add_option(
            name="valkey_address",
            typespec=str,
            default=os.environ.get("IP", "127.0.0.1"),
            help="The IPv4 address of the Valkey server to be connected"
        )
        loader.add_option(
            name="valkey_port",
            typespec=int,
            default=int(os.environ.get("PORT", "6379")),
            help="The port of the Valkey server to be connected"
        )
        loader.add_option(
            name="whitelist_filepath",
            typespec=Optional[str],
            default=os.path.join(os.environ.get("WHITELIST_DIR", os.getcwd()), "whitelist.txt"),
            help="""
            Path to whitelist.txt. Defaults to searching in the WHITELIST_DIR environment variable location. 
            Raises OptionsError if file cannot be found.
            """
        )
        loader.add_option(
            name="errorpage_filepath",
            typespec=Optional[str],
            default=os.path.join(os.environ.get("ERRPAGE_DIR", os.getcwd()), "403.html"),
            help="""
            Path to 403.html. Defaults to searching in the ERRPAGE_DIR environment variable location.
            If that fails, defaults to an plain-text html.
            """
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
            v = valkey.Valkey(host=self.valkey_address, port=self.valkey_port, db=0) # db=0 means database #0
            if (v.ping() is True):
                print(f"Valkey server is online @ IP {self.valkey_address} & port {self.valkey_port}")
            else:
                raise exceptions.OptionsError("Valkey server was initialized but failed to ping back")
        except:
            raise exceptions.OptionsError("Valkey server configuration failed")

        # Check if file exists at filepath
        filepath = ctx.options.whitelist_filepath
        if filepath is None or not os.path.isfile(filepath):
            raise exceptions.OptionsError("whitelist.txt was not found")
        
        # Determine if database should update by comparing checksums:
        with open(filepath, 'rb') as f:
            digest = hashlib.file_digest(f, "sha256")
        hsum = digest.hexdigest() # hexedecimal checksum
        
        with open(filepath, 'rt', encoding="utf_8") as f:
            old_hsum = v.get("whitelist_checksum").decode()
            if old_hsum == hsum:
                print("DEBUG: Checksum is unchanged -- moving on")
                return
            # Update checksum
            print("DEBUG: Checksum has changed -- reloading the database...")
            v.set("whitelist_checksum", hsum)
            # File is open and there's new content. Delete all entries from previous whitelist
            v.delete("whitelist")
            # Pipe contents into valkey databas
            pipe = v.pipeline()
            for line in f:
                domain = line.strip()
                pipe.sadd("whitelist", domain) # add domain to the set called "whitelist"
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

            # Try to fetch error page
            filepath = ctx.options.errorpage_filepath
            print(f"Debug: filepath = {filepath}")
            if filepath is None or not os.path.isfile(filepath):
                print("Warning! 403 page not set -- defaulting to plaintext")
                # Default error message:
                whitelist_403 = b"This website wasn't found on the whitelist!\n"
            else:
                with open(filepath, 'rb') as f:
                    whitelist_403 = f.read()
            flow.response = http.Response.make(
                status_code = 403,
                content = whitelist_403,
            )
        else:
            print(f"Domain {domain} was found in the whitelist!")

addons = [Valkey()] # is this line necessary?
