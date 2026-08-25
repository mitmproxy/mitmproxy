#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

# Security: No third-party dependencies here!

root = Path(__file__).absolute().parent.parent

if __name__ == "__main__":
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
        raise AssertionError

    # Upload binaries (be it release or snapshot)
    if tag:
        upload_dir = tag
    else:
        upload_dir = f"branches/{branch}"
    # Ideally we could have R2 pull from S3 automatically, but that's not possible yet. So we upload to both.
    print(f"Uploading binaries to snapshots.mitmproxy.org/{upload_dir}...")
    subprocess.check_call(
        [
            "aws",
            "s3",
            "sync",
            "--delete",
            *("--acl", "public-read"),
            *("--exclude", "*.msix"),
            root / "release/dist",
            f"s3://snapshots.mitmproxy.org/{upload_dir}",
        ]
    )
    if tag:
        # We can't scope R2 tokens, so they are only exposed in the deploy env.
        print(f"Uploading binaries to downloads.mitmproxy.org/{upload_dir}...")
        subprocess.check_call(
            [
                "aws",
                "s3",
                "sync",
                "--delete",
                *("--acl", "public-read"),
                *("--exclude", "*.msix"),
                *(
                    "--endpoint-url",
                    f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                ),
                root / "release/dist",
                f"s3://downloads/{upload_dir}",
            ],
            env={
                **os.environ,
                "AWS_REGION": "auto",
                "AWS_DEFAULT_REGION": "auto",
                "AWS_ACCESS_KEY_ID": os.environ["R2_ACCESS_KEY_ID"],
                "AWS_SECRET_ACCESS_KEY": os.environ["R2_SECRET_ACCESS_KEY"],
            },
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
