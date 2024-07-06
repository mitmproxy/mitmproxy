#!/usr/bin/env -S python3 -u
import datetime
import http.client
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Security: No third-party dependencies here!

root = Path(__file__).absolute().parent.parent


def get(url: str) -> http.client.HTTPResponse:
    assert url.startswith("https://")
    host, path = re.split(r"(?=/)", url.removeprefix("https://"), maxsplit=1)
    conn = http.client.HTTPSConnection(host)
    conn.request("GET", path, headers={"User-Agent": "mitmproxy/release-bot"})
    resp = conn.getresponse()
    print(f"HTTP {resp.status} {resp.reason}")
    return resp


def get_json(url: str) -> dict:
    resp = get(url)
    body = resp.read()
    try:
        return json.loads(body)
    except Exception as e:
        raise RuntimeError(f"{resp.status=} {body=}") from e


if __name__ == "__main__":
    version = sys.argv[1]
    assert re.match(r"^\d+\.\d+\.\d+$", version)
    major_version = int(version.split(".")[0])

    skip_branch_status_check = sys.argv[2] == "true"

    # changing this is useful for testing on a fork.
    repo = os.environ.get("GITHUB_REPOSITORY", "mitmproxy/mitmproxy")
    print(f"{version=} {skip_branch_status_check=} {repo=}")

    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    print("➡️ Working dir clean?")
    assert not subprocess.run(["git", "status", "--porcelain"]).stdout

    if skip_branch_status_check:
        print(f"⚠️ Skipping status check for {branch}.")
    else:
        print(f"➡️ CI is passing for {branch}?")
        assert (
            get_json(f"https://api.github.com/repos/{repo}/commits/{branch}/status")[
                "state"
            ]
            == "success"
        )

    print("➡️ Updating CHANGELOG.md...")
    changelog = root / "CHANGELOG.md"
    date = datetime.date.today().strftime("%d %B %Y")
    title = f"## {date}: mitmproxy {version}"
    cl = changelog.read_text("utf8")
    assert title not in cl
    cl, ok = re.subn(r"(?<=## Unreleased: mitmproxy next)", f"\n\n\n{title}", cl)
    assert ok == 1
    changelog.write_text(cl, "utf8")

    print("➡️ Updating web assets...")
    subprocess.run(["npm", "ci"], cwd=root / "web", check=True, capture_output=True)
    subprocess.run(
        ["npm", "start", "prod"], cwd=root / "web", check=True, capture_output=True
    )

    print("➡️ Updating version...")
    version_py = root / "mitmproxy" / "version.py"
    ver = version_py.read_text("utf8")
    ver, ok = re.subn(r'(?<=VERSION = ")[^"]+', version, ver)
    assert ok == 1
    version_py.write_text(ver, "utf8")

    print("➡️ Do release commit...")
    subprocess.run(
        ["git", "config", "user.email", "noreply@mitmproxy.org"], cwd=root, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "mitmproxy release bot"], cwd=root, check=True
    )
    subprocess.run(
        ["git", "commit", "-a", "-m", f"mitmproxy {version}"], cwd=root, check=True
    )
    tag_name = f"v{version}"
    subprocess.run(["git", "tag", tag_name], cwd=root, check=True)
    release_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    if branch == "main":
        print("➡️ Bump version...")
        next_dev_version = f"{major_version + 1}.0.0.dev"
        ver, ok = re.subn(r'(?<=VERSION = ")[^"]+', next_dev_version, ver)
        assert ok == 1
        version_py.write_text(ver, "utf8")

        print("➡️ Reopen main for development...")
        subprocess.run(
            ["git", "commit", "-a", "-m", f"reopen main for development"],
            cwd=root,
            check=True,
        )

    print("➡️ Pushing...")
    subprocess.run(
        ["git", "push", "--atomic", "origin", branch, tag_name], cwd=root, check=True
    )

    print("➡️ Creating release on GitHub...")
    subprocess.run(
        [
            "gh",
            "release",
            "create",
            tag_name,
            "--title",
            f"mitmproxy {version}",
            "--notes-file",
            "release/github-release-notes.txt",
        ],
        cwd=root,
        check=True,
    )

    print("➡️ Dispatching release workflow...")
    subprocess.run(
        ["gh", "workflow", "run", "main.yml", "--ref", tag_name], cwd=root, check=True
    )

    print("")
    print("✅ CI is running now.")

    while True:
        print("⌛ Waiting for CI...")
        workflows = get_json(
            f"https://api.github.com/repos/{repo}/actions/runs?head_sha={release_sha}"
        )["workflow_runs"]

        all_done = True
        if not workflows:
            all_done = False  # we expect to have at least one workflow.
        for workflow in workflows:
            if workflow["status"] != "completed":
                all_done = False
            if workflow["status"] == "waiting":
                print(f"⚠️ CI is waiting for approval: {workflow['html_url']}")

        if all_done:
            for workflow in workflows:
                if workflow["conclusion"] != "success":
                    print(f"⚠️ {workflow['display_title']} workflow run failed.")
            break
        else:
            time.sleep(30)  # relatively strict rate limits here.

    print("➡️ Checking GitHub Releases...")
    resp = get(f"https://api.github.com/repos/{repo}/releases/tags/{tag_name}")
    assert resp.status == 200

    print("➡️ Checking PyPI...")
    pypi_data = get_json("https://pypi.org/pypi/mitmproxy/json")
    assert version in pypi_data["releases"]

    print("➡️ Checking docs archive...")
    resp = get(f"https://docs.mitmproxy.org/archive/v{major_version}/")
    assert resp.status == 200

    print(f"➡️ Checking Docker ({version} tag)...")
    resp = get(
        f"https://hub.docker.com/v2/repositories/mitmproxy/mitmproxy/tags/{version}"
    )
    assert resp.status == 200

    if branch == "main":
        print("➡️ Checking Docker (latest tag)...")
        docker_latest_data = get_json(
            "https://hub.docker.com/v2/repositories/mitmproxy/mitmproxy/tags/latest"
        )
        docker_last_updated = datetime.datetime.fromisoformat(
            docker_latest_data["last_updated"].replace("Z", "+00:00")
        )
        print(f"Last update: {docker_last_updated.isoformat(timespec='minutes')}")
        assert docker_last_updated > datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(hours=2)

    print("")
    print("✅ All done. 🥳")
    print("")
