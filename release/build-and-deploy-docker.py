#!/usr/bin/env python3
"""
Building and deploying docker images is a bit of a special snowflake as we don't get a file we can upload/download
as an artifact. So we need to do everything in one job.
"""

import os
import shutil
import subprocess
from pathlib import Path

# Security: No third-party dependencies here!

root = Path(__file__).absolute().parent.parent

ref = os.environ["GITHUB_REF"]
branch: str | None = None
tag: str | None = None
if ref.startswith("refs/heads/"):
    branch = ref.replace("refs/heads/", "")
elif ref.startswith("refs/tags/"):
    if not ref.startswith("refs/tags/v"):
        raise AssertionError(f"Unexpected tag: {ref}")
    tag = ref.replace("refs/tags/v", "")
else:
    raise AssertionError("Failed to parse $GITHUB_REF")

(whl,) = root.glob("release/dist/mitmproxy-*-py3-none-any.whl")
docker_build_dir = root / "release/docker"
shutil.copy(whl, docker_build_dir / whl.name)

# Build for this platform and test if it runs.
subprocess.check_call(
    [
        "docker",
        "buildx",
        "build",
        "--tag",
        "localtesting",
        "--load",
        "--build-arg",
        f"MITMPROXY_WHEEL={whl.name}",
        ".",
    ],
    cwd=docker_build_dir,
)
r = subprocess.run(
    [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{root / 'release'}:/release",
        "localtesting",
        "mitmdump",
        "-s",
        "/release/selftest.py",
    ],
    capture_output=True,
)
print(r.stdout.decode())
assert "Self-test successful" in r.stdout.decode()
assert r.returncode == 0

# Now we can deploy.
subprocess.check_call(
    [
        "docker",
        "login",
        "-u",
        os.environ["DOCKER_USERNAME"],
        "-p",
        os.environ["DOCKER_PASSWORD"],
    ]
)


def _buildx(docker_tag):
    subprocess.check_call(
        [
            "docker",
            "buildx",
            "build",
            "--tag",
            docker_tag,
            "--push",
            "--platform",
            "linux/amd64,linux/arm64",
            "--build-arg",
            f"MITMPROXY_WHEEL={whl.name}",
            ".",
        ],
        cwd=docker_build_dir,
    )


if branch == "main":
    _buildx("mitmproxy/mitmproxy:dev")
elif branch == "citest":
    _buildx("mitmproxy/mitmproxy:citest")
elif tag:
    _buildx(f"mitmproxy/mitmproxy:{tag}")
    _buildx("mitmproxy/mitmproxy:latest")
else:
    raise AssertionError
