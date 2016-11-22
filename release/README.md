# Release Checklist

- Verify that all CI tests pass for current master
- Tag the release, and push to Github
- Wait for tag CI to complete
- Download assets from snapshots.mitmproxy.org
- Create release notice on Github
- Upload wheel to pypi
- Update docker-releases repo
