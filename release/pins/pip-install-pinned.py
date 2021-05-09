#!/usr/bin/env python3
import platform
import sys
from pathlib import Path
from subprocess import check_call

here = Path(__file__).parent

pip_install = [
    sys.executable, "-m",
    "pip",
    "install",
    "--disable-pip-version-check",
]

check_call([*pip_install, "--require-hashes", "-r", f"requirements-{platform.system().lower()}.txt"], cwd=here)
check_call([*pip_install, "--no-deps", "-e", "../.."], cwd=here)
