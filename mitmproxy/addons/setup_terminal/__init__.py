import os

from flask import Flask
from flask import jsonify
from flask import render_template
from flask import Response

from mitmproxy import ctx
from mitmproxy import http
from mitmproxy.addons import asgiapp

app = Flask(__name__)


def get_setup_vars():
    """Get proxy and certificate variables for setup scripts."""
    proxy_host = app.config.get("PROXY_HOST", "127.0.0.1")
    proxy_port = app.config.get("PROXY_PORT", 8080)
    confdir = app.config.get("CONFDIR")

    confdir = os.path.expanduser(confdir)
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    cert_path = f"{confdir}/mitmproxy-ca-cert.pem"

    return {
        "proxy_url": proxy_url,
        "cert_path": cert_path,
    }


@app.route("/setup")
def setup():
    """Return proxy configuration as JSON."""
    proxy_host = app.config.get("PROXY_HOST", "127.0.0.1")
    proxy_port = app.config.get("PROXY_PORT", 8080)
    confdir = app.config.get("CONFDIR")

    base_url = f"http://{proxy_host}:{proxy_port}"
    return jsonify({
        "proxy_url": f"{proxy_host}:{proxy_port}",
        "proxy_host": proxy_host,
        "proxy_port": proxy_port,
        "certificates": {
            "pem": f"{confdir}/mitmproxy-ca-cert.pem",
            "p12": f"{confdir}/mitmproxy-ca-cert.p12",
            "cer": f"{confdir}/mitmproxy-ca-cert.cer",
        },
        "setup_scripts": {
            "sh": f"{base_url}/setup.sh",
            "bash": f"{base_url}/setup.sh",
            "zsh": f"{base_url}/setup.sh",
            "ksh": f"{base_url}/setup.sh",
            "fish": f"{base_url}/setup.fish",
            "powershell": f"{base_url}/setup.ps1",
            "pwsh": f"{base_url}/setup.ps1",
        },
    })


@app.route("/setup.sh")
def setup_sh():
    """Return bash script with environment variables."""
    return Response(
        render_template("setup.sh", **get_setup_vars()),
        mimetype="text/x-shellscript",
    )


@app.route("/setup.fish")
def fish_setup():
    """Return fish shell script with environment variables."""
    return Response(
        render_template("setup.fish", **get_setup_vars()),
        mimetype="application/x-fish",
    )


@app.route("/setup.ps1")
def ps_setup():
    """Return PowerShell script with environment variables."""
    return Response(
        render_template("setup.ps1", **get_setup_vars()),
        mimetype="text/plain",
    )


class SetupTerminal(asgiapp.WSGIApp):
    """
    An addon that hosts terminal setup endpoints within mitmproxy at mitm.it.

    Provides automatic shell environment configuration scripts for bash, fish, and PowerShell.
    """

    name = "setup_terminal"

    def __init__(self):
        super().__init__(app, None, None)

    def should_serve(self, flow: http.HTTPFlow) -> bool:
        """Serve setup endpoints on any host."""
        setup_paths = {"/setup", "/setup.sh", "/setup.fish", "/setup.ps1"}
        return (
            flow.request.path in setup_paths
            and flow.live
        )

    def load(self, loader):
        loader.add_option(
            "setup_terminal",
            bool,
            True,
            "Toggle the mitmproxy terminal setup app."
        )

    def configure(self, updated):
        # Extract and store proxy server info
        proxyserver = ctx.master.addons.get("proxyserver")
        if proxyserver and proxyserver.servers:
            first_server = next(iter(proxyserver.servers))
            if first_server.listen_addrs:
                host, port = first_server.listen_addrs[0][:2]
                app.config["PROXY_HOST"] = host if host else "127.0.0.1"
                app.config["PROXY_PORT"] = port
            else:
                app.config["PROXY_HOST"] = ctx.options.listen_host or "127.0.0.1"
                app.config["PROXY_PORT"] = ctx.options.listen_port or 8080
        else:
            app.config["PROXY_HOST"] = ctx.options.listen_host or "127.0.0.1"
            app.config["PROXY_PORT"] = ctx.options.listen_port or 8080

        app.config["CONFDIR"] = ctx.options.confdir

    async def request(self, f):
        if ctx.options.setup_terminal:
            await super().request(f)
