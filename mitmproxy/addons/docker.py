import logging
import shutil
import subprocess
import tempfile
import json
import os
from mitmproxy import command
from mitmproxy import ctx
from mitmproxy.log import ALERT


class Docker:
    
    @command.command("docker.enable")
    def enable(self) -> None:
    # def start(self) -> None:
        """
        Enable docker proxy to started [Make sure to run `docker.disable` when done]
        Rebuild container after enabling this option
        """
        if not shutil.which("docker"):
            logging.log(
                    ALERT, "Docker not installed or not avaialble in path"
                )
            return
        
        config = {}
        config_path = os.path.join(os.path.expanduser('~'),".docker","config.json")
        with open(config_path,"r") as file:
            config = json.load(file)
            config['proxies'] = {
                "default" : {
                    "httpProxy": 'http://host.docker.internal:{}/'.format(ctx.options.listen_port or "8080"),
                    "httpsProxy": 'https://host.docker.internal:{}/'.format(ctx.options.listen_port or "8080"),
                }
            }
            logging.debug(config)

        with open(config_path,"w") as file:
            json.dump(config,file)

        logging.log(ALERT,"Enabled proxy [updated:~/.docker/config.json]")

    @command.command("docker.disable")
    def disable(self) -> None:
    # def start(self) -> None:
        """
        Disable docker proxy [Rebuild container after disabling this option]
        """
        if not shutil.which("docker"):
            logging.log(
                    ALERT, "Docker not installed or not avaialble in path"
                )
            return
        
        config = {}
        config_path = os.path.join(os.path.expanduser('~'),".docker","config.json")
        with open(config_path,"r") as file:
            config = json.load(file)
            config['proxies'] = {}
            logging.debug(config)

        with open(config_path,"w") as file:
            json.dump(config,file)
