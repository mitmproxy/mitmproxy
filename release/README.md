# Release Checklist

- Update CHANGELOG
- Verify that all CI tests pass for current master
- Tag the release, and push to Github
- Wait for tag CI to complete
- Download assets from https://snapshots.mitmproxy.org
- Create release notice on Github
- Upload wheel to pypi (`twine upload wheelname`)
- Update docker-releases repo
  - Create a new branch based of master for major versions.
  - Add a commit that pins dependencies like so: https://github.com/mitmproxy/docker-releases/commit/3d6a9989fde068ad0aea257823ac3d7986ff1613. 
    * The requirements can be obtained by creating a fresh venv, pip-installing the new wheel in there, and then running `pip freeze`.
    * `virtualenv -ppython3.5 venv && source venv/bin/activate && pip install mitmproxy && pip freeze`
- Update `latest` tag on https://hub.docker.com/r/mitmproxy/mitmproxy/~/settings/automated-builds/
- Bump the version in https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/version.py and update https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/io_compat.py in the next commit
