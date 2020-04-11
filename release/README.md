# Release Checklist

These steps assume you are on the correct branch and have a git remote called `origin` that points to the `mitmproxy/mitmproxy` repo. If necessary, create a major version branch starting off the release tag (e.g. `git checkout -b v4.x v4.0.0`) first.

- Update CHANGELOG.
- Verify that the compiled mitmweb assets are up-to-date.
- Verify that all CI tests pass.
- Verify that `mitmproxy/version.py` is correct. Remove `.dev` suffix if it exists.
- Tag the release and push to Github.
    - `git tag v4.0.0`
    - `git push origin v4.0.0`
- Wait for tag CI to complete.

### GitHub Releases
- Create release notice on Github
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
  `brew bump-formula-pr --url https://github.com/mitmproxy/mitmproxy/archive/v<version number here>`

### Docker
- The docker image is built by our CI workers and pushed to Docker Hub automatically.
- Please verify that https://hub.docker.com/r/mitmproxy/mitmproxy/tags/ has the latest version.
- The latest and latest-ARMv7 tags should auto-update. @mhils introduced this after the 5.0.0 release.
  Please verify that this is the case and remove this notice. For reference, this is how to do it manually:
  `export VERSION=4.0.3 && docker pull mitmproxy/mitmproxy:$VERSION && docker tag mitmproxy/mitmproxy:$VERSION mitmproxy/mitmproxy:latest && docker push mitmproxy/mitmproxy:latest`.

### Docs
  - `./build-current`. If everything looks alright, continue with
  - `./upload-stable`,
  - `./build-archive`, and
  - `./upload-archive v4`. Doing this now already saves you from switching back to an old state on the next release.

### Website
 - Update version here:
   https://github.com/mitmproxy/www/blob/master/src/config.toml
 - Update docs menu here:
   https://github.com/mitmproxy/www/blob/master/src/themes/mitmproxy/layouts/partials/header.html
 - Run `./build && ./upload-test`.
 - If everything looks alright at https://www-test.mitmproxy.org, run `./upload-prod`.


### Prepare for next release
 - Last but not least, bump the major version on master in
   [https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/version.py](mitmproxy/version.py) and add a `.dev` suffix.
