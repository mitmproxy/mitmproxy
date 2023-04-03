import subprocess
from shutil import which

l = subprocess.Popen(["docker", "run", "mitm"])

if which("docker"):
    print(l)
