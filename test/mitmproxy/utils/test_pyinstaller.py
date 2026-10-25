import runpy
import sys
from pathlib import Path


def test_cryptography_hook_collects_abi3t_dll(monkeypatch, tmp_path):
    compat_dir = tmp_path / "DLLs" / "abi3t_compat"
    compat_dir.mkdir(parents=True)
    python3t_dll = compat_dir / "python3t.dll"
    python3t_dll.touch()

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "base_prefix", str(tmp_path))
    hook = runpy.run_path(
        str(
            Path(__file__).parents[3]
            / "mitmproxy"
            / "utils"
            / "pyinstaller"
            / "hook-cryptography.py"
        )
    )

    assert hook["binaries"] == [(str(python3t_dll), ".")]
    assert hook["hiddenimports"] == [
        "cryptography.hazmat.bindings._rust",
        "cryptography.hazmat.bindings._rust.openssl",
    ]
