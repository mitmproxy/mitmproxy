# Release Checklist

- Update CHANGELOG
- Verify that all CI tests pass for current master
- Tag the release, and push to Github
- Wait for tag CI to complete
- Download assets from snapshots.mitmproxy.org
- Create release notice on Github
- Upload wheel to pypi (`twine upload wheelname`)
- Update docker-releases repo
- Update `latest` tag on https://hub.docker.com/r/mitmproxy/mitmproxy/~/settings/automated-builds/
- Bump the version in https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/version.py and update https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/io_compat.py in the next commit
