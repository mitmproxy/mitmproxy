# Release Checklist

Make sure to run all these steps on the correct branch you want to create a new
release for! The command examples assume that you have a git remote called
`upstream` that points to the `mitmproxy/mitmproxy` repo.

- Verify that `mitmproxy/version.py` is correct
- Update CHANGELOG
- Verify that all CI tests pass
- If needed, create a major version branch - e.g. `v4.x`. Assuming you have a remote repo called `upstream` that points to the mitmproxy/mitmproxy repo::
  - `git checkout -b v4.x upstream/master`
  - `git push -u upstream v4.x`
- Tag the release and push to Github
    - `git tag v4.0.0`
    - `git push upstream v4.0.0`
- Wait for tag CI to complete

## GitHub Release
- Create release notice on Github
  [here](https://github.com/mitmproxy/mitmproxy/releases/new) if not already
  auto-created by the tag.
- We DO NOT upload release artifacts to GitHub anymore. Simply add the
  following snippet to the notice:
  `You can find the latest release packages on our snapshot server: https://snapshots.mitmproxy.org/v<version number here>`

## PyPi
- The created wheel is uploaded to PyPi automatically
- Please check https://pypi.python.org/pypi/mitmproxy about the latest version

## Homebrew
- The Homebrew maintainers are typically very fast and detect our new relese
  within a day.
- If you feel the need, you can run this from a macOS machine:
  `brew bump-formula-pr --url https://github.com/mitmproxy/mitmproxy/archive/v<version number here>`

## Docker
- The docker image is built on Travis and pushed to Docker Hub automatically.
- Please check https://hub.docker.com/r/mitmproxy/mitmproxy/tags/ about the latest version
- Update `latest` tag: `docker tag mitmproxy/mitmproxy:<version number here> mitmproxy/mitmproxy:latest && docker push mitmproxy/mitmproxy:latest`

## Website
 - Update version here:
   https://github.com/mitmproxy/www/blob/master/src/config.toml
 - Run `./build && ./upload-test`
 - If everything looks alright, run `./upload-prod`

## Docs
  - Make sure you've uploaded the previous version's docs to archive
  - If everything looks alright:
    - `./build-current`
    - `./upload-stable`

## Prepare for next release
 - Last but not least, bump the version on master in
   [https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/version.py](mitmproxy/version.py) for major releases.
