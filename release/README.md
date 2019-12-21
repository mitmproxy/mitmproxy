# Release Checklist

These steps assume you are on the correct branch and have a git remote called `origin` that points to the `mitmproxy/mitmproxy` repo. If necessary, create a major version branch starting off the release tag (e.g. `git checkout -b v4.x v4.0.0`) first.

- Update CHANGELOG.
- Verify that all CI tests pass.
- Verify that `mitmproxy/version.py` is correct. Remove `.dev` suffix if it exists.
- Tag the release and push to Github.
    - `git tag v4.0.0`
    - `git push origin v4.0.0`
- Wait for tag CI to complete.

## GitHub Release
- Create release notice on Github
  [here](https://github.com/mitmproxy/mitmproxy/releases/new) if not already
  auto-created by the tag.
- We DO NOT upload release artifacts to GitHub anymore. Simply add the
  following snippet to the notice:
  `You can find the latest release packages at https://mitmproxy.org/downloads/.`

## PyPi
- The created wheel is uploaded to PyPi automatically.
- Please check https://pypi.python.org/pypi/mitmproxy about the latest version.

## Homebrew
- The Homebrew maintainers are typically very fast and detect our new relese
  within a day.
- If you feel the need, you can run this from a macOS machine:
  `brew bump-formula-pr --url https://github.com/mitmproxy/mitmproxy/archive/v<version number here>`

## Docker
- The docker image is built on Travis and pushed to Docker Hub automatically.
- Please check https://hub.docker.com/r/mitmproxy/mitmproxy/tags/ about the latest version.
- Update `latest` tag: `export VERSION=4.0.3 && docker pull mitmproxy/mitmproxy:$VERSION && docker tag mitmproxy/mitmproxy:$VERSION mitmproxy/mitmproxy:latest && docker push mitmproxy/mitmproxy:latest`.

## Website
 - Update version here:
   https://github.com/mitmproxy/www/blob/master/src/config.toml
 - Run `./build && ./upload-test`.
 - If everything looks alright at http://www-test.mitmproxy.org, run `./upload-prod`.

## Docs
  - Make sure you've uploaded the previous version's docs to archive
  - If everything looks alright:
    - `./build-current`
    - `./upload-stable`

## Prepare for next release
 - Last but not least, bump the major version on master in
   [https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/version.py](mitmproxy/version.py) and add a `.dev` suffix.
