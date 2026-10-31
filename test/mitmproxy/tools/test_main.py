import shutil

import pytest

from mitmproxy import options
from mitmproxy.tools import main

shutdown_script = "mitmproxy/data/addonscripts/shutdown.py"


def test_mitmweb(tdata):
    main.mitmweb(
        [
            "--no-web-open-browser",
            "-s",
            tdata.path(shutdown_script),
            "-q",
            "-p",
            "0",
            "--web-port",
            "0",
        ]
    )


def test_mitmdump(tdata):
    main.mitmdump(
        [
            "-s",
            tdata.path(shutdown_script),
            "-q",
            "-p",
            "0",
        ]
    )


def test_options_includes_addon_options(tdata, capsys):
    """--options should include options registered by addon scripts."""
    with pytest.raises(SystemExit):
        main.mitmdump(
            [
                "-s",
                tdata.path("mitmproxy/data/addonscripts/custom_option.py"),
                "--options",
            ]
        )
    output = capsys.readouterr().out
    assert "custom_addon_option" in output


def test_options_without_scripts(capsys):
    """--options without any scripts should still work and list built-in options."""
    with pytest.raises(SystemExit):
        main.mitmdump(["--options"])
    output = capsys.readouterr().out
    assert "listen_port" in output
    assert "custom_addon_option" not in output


def test_mitmdump_cert_passphrase_from_config_file(tdata, tmp_path):
    """An encrypted CA in --set confdir=... can be opened with the cert_passphrase from that confdir's config.yaml."""
    shutil.copy(
        tdata.path("mitmproxy/data/mitmproxy.pem"), tmp_path / "mitmproxy-ca.pem"
    )
    (tmp_path / "config.yaml").write_text("cert_passphrase: password\n")
    main.mitmdump(
        [
            "-s",
            tdata.path(shutdown_script),
            "-q",
            "-p",
            "0",
            "--set",
            f"confdir={tmp_path}",
        ]
    )


def test_apply_startup_options(tmp_path):
    (tmp_path / "config.yaml").write_text(
        "cert_passphrase: from-config\nunknown_addon_option: 42\n"
    )
    opts = options.Options()
    seen = []

    def changed(o, updated):
        seen.append((o.confdir, o.cert_passphrase))

    opts.subscribe(changed, ["confdir", "cert_passphrase"])
    main.apply_startup_options(
        opts,
        [f"confdir={tmp_path}", "cert_passphrase=from-set", "listen_port=1234"],
    )
    # one update with the final values; the config file still overrides --set
    assert seen == [(str(tmp_path), "from-config")]
    assert opts.listen_port == 1234
    assert opts.deferred == {"unknown_addon_option": 42}
