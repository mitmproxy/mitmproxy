# Release Checklist

These steps assume you are on the correct branch and have a git remote called `origin` that points to the `mitmproxy/mitmproxy` repo. If necessary, create a major version branch starting off the release tag (e.g. `git checkout -b v4.x v4.0.0`) first.

- Update CHANGELOG.
- Verify that the compiled mitmweb assets are up-to-date.
- Verify that all CI tests pass.
- Verify that `mitmproxy/version.py` is correct. Remove `.dev` suffix if it exists.
- Tag the release and push to GitHub.
  - `git tag v4.0.0`
  - `git push origin v4.0.0`
- Wait for tag CI to complete.

### GitHub Releases

- Create release notice on GitHub
  [here](https://github.com/mitmproxy/mitmproxy/releases/new) if not already
  auto-created by the tag.
- We DO NOT upload release artifacts to GitHub anymore. Simply add the
  following snippet to the notice:
  `You can find the latest release packages at https://mitmproxy.org/downloads/.`

### PyPi

- The created wheel is uploaded to PyPi automatically.
- Please verify that https://pypi.python.org/pypi/mitmproxy has the latest version.

### Homebrew

- The Homebrew maintainers are typically very fast and detect our new relese
  within a day.
- If you feel the need, you can run this from a macOS machine:
  `brew bump-formula-pr --url https://github.com/mitmproxy/mitmproxy/archive/v<version number here>.tar.gz mitmproxy`

### Docker

- The docker image is built by our CI workers and pushed to Docker Hub automatically.
- Please verify that https://hub.docker.com/r/mitmproxy/mitmproxy/tags/ has the latest version.
- Please verify that the latest tag points to the most recent image (same digest / hash).

### Docs

- `./build.py`. If everything looks alright, continue with
- `./upload-stable.sh`,
- `DOCS_ARCHIVE=true ./build.py`, and
- `./upload-archive.sh v4`. Doing this now already saves you from switching back to an old state on the next release.

### Website

- The website does not need to be updated for patch releases. New versions are automatically picked up once they are on the download server.
- Update version here:
   https://github.com/mitmproxy/www/blob/main/src/config.toml
- Update docs menu here:
   https://github.com/mitmproxy/www/blob/main/src/themes/mitmproxy/layouts/partials/header.html
- Run `./build && ./upload-test`.
- If everything looks alright at https://www-test.mitmproxy.org, run `./upload-prod`.

### Prepare for next release

- Last but not least, bump the major version on main in
   [https://github.com/mitmproxy/mitmproxy/blob/main/mitmproxy/version.py](mitmproxy/version.py) and add a `.dev` suffix.
