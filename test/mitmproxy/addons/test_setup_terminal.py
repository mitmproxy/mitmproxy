import json

import pytest

from mitmproxy.addons import setup_terminal
from mitmproxy.test import taddons


@pytest.fixture
def client():
    with setup_terminal.app.test_client() as client:
        yield client


class TestSetupTerminal:
    def test_setup_json(self, client, tdata):
        """Test /setup endpoint returns valid JSON with proxy config."""
        addon = setup_terminal.SetupTerminal()
        with taddons.context(addon) as tctx:
            tctx.configure(addon, confdir=tdata.path("mitmproxy/data/confdir"))
            resp = client.get("/setup")
            assert resp.status_code == 200
            assert "application/json" in resp.content_type

            data = json.loads(resp.data)
            assert "proxy_url" in data
            assert "proxy_host" in data
            assert "proxy_port" in data
            assert "certificates" in data
            assert "setup_scripts" in data

            # Check proxy format
            assert ":" in data["proxy_url"]
            assert data["proxy_port"] == 8080

            # Check certificate paths
            assert data["certificates"]["pem"].endswith(".pem")
            assert data["certificates"]["p12"].endswith(".p12")
            assert data["certificates"]["cer"].endswith(".cer")

            # Check setup scripts with shell aliases
            assert data["setup_scripts"]["sh"] == data["setup_scripts"]["bash"]
            assert data["setup_scripts"]["bash"] == data["setup_scripts"]["zsh"]
            assert data["setup_scripts"]["zsh"] == data["setup_scripts"]["ksh"]
            assert data["setup_scripts"]["fish"].endswith("/setup.fish")
            assert data["setup_scripts"]["powershell"] == data["setup_scripts"]["pwsh"]
            assert data["setup_scripts"]["powershell"].endswith("/setup.ps1")

    def test_setup_sh_endpoint(self, client, tdata):
        """Test /setup.sh endpoint returns bash script."""
        addon = setup_terminal.SetupTerminal()
        with taddons.context(addon) as tctx:
            tctx.configure(addon, confdir=tdata.path("mitmproxy/data/confdir"))
            resp = client.get("/setup.sh")
            assert resp.status_code == 200
            assert "text/x-shellscript" in resp.content_type
            assert b"export HTTP_PROXY=" in resp.data
            assert b"export HTTPS_PROXY=" in resp.data
            assert b"export MITMPROXY_ACTIVE=" in resp.data

    def test_setup_fish_endpoint(self, client, tdata):
        """Test /setup.fish endpoint returns fish script."""
        addon = setup_terminal.SetupTerminal()
        with taddons.context(addon) as tctx:
            tctx.configure(addon, confdir=tdata.path("mitmproxy/data/confdir"))
            resp = client.get("/setup.fish")
            assert resp.status_code == 200
            assert resp.content_type == "application/x-fish"
            assert b"set -gx HTTP_PROXY" in resp.data
            assert b"set -gx HTTPS_PROXY" in resp.data
            assert b"set -gx MITMPROXY_ACTIVE" in resp.data

    def test_setup_ps1_endpoint(self, client, tdata):
        """Test /setup.ps1 endpoint returns PowerShell script."""
        addon = setup_terminal.SetupTerminal()
        with taddons.context(addon) as tctx:
            tctx.configure(addon, confdir=tdata.path("mitmproxy/data/confdir"))
            resp = client.get("/setup.ps1")
            assert resp.status_code == 200
            assert "text/plain" in resp.content_type
            assert b"$Env:HTTP_PROXY" in resp.data
            assert b"$Env:HTTPS_PROXY" in resp.data
            assert b"Stop-Intercepting" in resp.data

    def test_setup_vars_interpolation(self, client, tdata):
        """Test that setup variables are correctly interpolated."""
        addon = setup_terminal.SetupTerminal()
        with taddons.context(addon) as tctx:
            tctx.configure(addon, confdir=tdata.path("mitmproxy/data/confdir"))
            resp = client.get("/setup.sh")
            content = resp.data.decode()

            # Check that proxy variables are interpolated (not template strings)
            assert "{{ proxy_url }}" not in content
            assert "{{ cert_path }}" not in content
            # Should contain actual values
            assert "http://" in content
            assert ".pem" in content

    def test_addon_initialization(self, tdata):
        """Test addon initializes correctly."""
        addon = setup_terminal.SetupTerminal()
        assert addon.name == "setup_terminal"

    def test_addon_configure(self, tdata):
        """Test addon configure method sets Flask config."""
        addon = setup_terminal.SetupTerminal()
        with taddons.context(addon) as tctx:
            tctx.configure(addon, confdir=tdata.path("mitmproxy/data/confdir"))
            # Verify Flask app config was updated
            assert setup_terminal.app.config.get("CONFDIR") is not None

    def test_should_serve(self):
        """Test should_serve method correctly identifies setup paths."""
        addon = setup_terminal.SetupTerminal()
        from mitmproxy.test import tflow

        # Test setup paths are served
        for path in ["/setup", "/setup.sh", "/setup.fish", "/setup.ps1"]:
            f = tflow.tflow()
            f.request.path = path
            assert addon.should_serve(f)

        # Test other paths are not served
        f = tflow.tflow()
        f.request.path = "/other"
        assert not addon.should_serve(f)
