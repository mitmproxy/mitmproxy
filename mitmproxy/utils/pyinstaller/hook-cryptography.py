import sys
from pathlib import Path

hiddenimports = [
    "cryptography.hazmat.bindings._rust",
    "cryptography.hazmat.bindings._rust.openssl",
]

binaries = []
if sys.platform == "win32":
    python3t_dll = (
        Path(sys.base_prefix) / "DLLs" / "abi3t_compat" / "python3t.dll"
    )
    if python3t_dll.is_file():
        binaries.append((str(python3t_dll), "."))
