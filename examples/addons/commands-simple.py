"""Add a custom command to mitmproxy's command prompt."""

import logging

from mitmproxy import command


class MyAddon:
    def __init__(self):
        self.num = 0

    @command.command("myaddon.inc")
    def inc(self) -> None:
        self.num += 1
        logging.info(f"num = {self.num}")


addons = [MyAddon()]
