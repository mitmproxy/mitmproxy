#!/usr/bin/env python3
import os
import re
import subprocess
from pathlib import Path
from typing import Optional
# Security: No third-party dependencies here!

if __name__ == "__main__":
    ref = os.environ["GITHUB_REF"]
    branch: Optional[str] = None
    tag: Optional[str] = None
    if ref.startswith("refs/heads/"):
        branch = ref.replace("refs/heads/", "")
    elif ref.startswith("refs/tags/"):
        tag = ref.replace("refs/tags/", "")
    else:
        raise AssertionError

    # Upload binaries (be it release or snapshot)
    if tag:
        # remove "v" prefix from version tags.
        upload_dir = re.sub(r"^v([\d.]+)$", r"\1", tag)
    else:
        upload_dir = f"branches/{branch}"
    subprocess.check_call([
        "aws", "s3", "cp",
        "--acl", "public-read",
        f"./release/dist/",
        f"s3://snapshots.mitmproxy.org/{upload_dir}/",
        "--recursive",
    ])

    # Upload releases to PyPI
    if tag:
        whl, = Path("release/dist/").glob('mitmproxy-*-py3-none-any.whl')
        subprocess.check_call(["twine", "upload", whl])

    # Upload dev docs
    if branch == "main" or branch == "actions-hardening":  # FIXME remove
        subprocess.check_call([
            "aws", "configure",
            "set", "preview.cloudfront", "true"
        ])
        subprocess.check_call([
            "aws", "s3",
            "sync",
            "--delete",
            "--acl", "public-read",
            "docs/public",
            "s3://docs.mitmproxy.org/dev"
        ])
        subprocess.check_call([
            "aws", "cloudfront",
            "create-invalidation",
            "--distribution-id", "E1TH3USJHFQZ5Q",
            "--paths", "/dev/*"
        ])
