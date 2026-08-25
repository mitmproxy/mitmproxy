import pytest

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
