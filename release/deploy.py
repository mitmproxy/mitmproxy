#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
from typing import Optional

# Security: No third-party dependencies here!

root = Path(__file__).absolute().parent.parent

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
        upload_dir = tag
    else:
        upload_dir = f"branches/{branch}"
    print(f"Uploading binaries to snapshots.mitmproxy.org/{upload_dir}...")
    subprocess.check_call(
        [
            "aws",
            "s3",
            "sync",
            "--delete",
            "--acl",
            "public-read",
            "--exclude",
            "*.msix",
            root / "release/dist",
            f"s3://snapshots.mitmproxy.org/{upload_dir}",
        ]
    )

    # Upload releases to PyPI
    if tag:
        print(f"Uploading wheel to PyPI...")
        (whl,) = root.glob("release/dist/mitmproxy-*-py3-none-any.whl")
        subprocess.check_call(["twine", "upload", whl])

    # Upload docs
    def upload_docs(path: str, src: Path = root / "docs/public"):
        subprocess.check_call(["aws", "configure", "set", "preview.cloudfront", "true"])
        subprocess.check_call(
            [
                "aws",
                "s3",
                "sync",
                "--delete",
                "--acl",
                "public-read",
                src,
                f"s3://docs.mitmproxy.org{path}",
            ]
        )
        subprocess.check_call(
            [
                "aws",
                "cloudfront",
                "create-invalidation",
                "--distribution-id",
                "E1TH3USJHFQZ5Q",
                "--paths",
                f"{path}/*",
            ]
        )

    if branch == "main":
        print(f"Uploading dev docs...")
        upload_docs("/dev")
    if tag:
        print(f"Uploading release docs...")
        upload_docs("/stable")
        upload_docs(f"/archive/v{tag.split('.')[0]}", src=root / "docs/archive")
