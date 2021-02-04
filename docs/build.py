#!/usr/bin/env python3
import shutil
import subprocess
from pathlib import Path


here = Path(__file__).parent

for script in (here / "scripts").glob("*.py"):
    print(f"Generating output for {script.name}...")
    out = subprocess.check_output(["python3", script.absolute()], text=True)
    if out:
        (here / "src" / "generated" / f"{script.stem}.html").write_text(out)

if (here / "public").exists():
    shutil.rmtree(here / "public")
subprocess.run(["hugo"], cwd=here / "src")
