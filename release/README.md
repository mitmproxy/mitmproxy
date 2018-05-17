# Release Checklist

Make sure to run all these steps on the correct branch you want to create a new
release for! The command examples assume that you have a git remote called
`upstream` that points to the `mitmproxy/mitmproxy` repo.

- Verify that `mitmproxy/version.py` is correct
- Update CHANGELOG
- Verify that all CI tests pass
- Create a major version branch - e.g. `v4.x`. Assuming you have a remote repo called `upstream` that points to the mitmproxy/mitmproxy repo::
  - `git checkout -b v4.x upstream/master`
  - `git push -u upstream v4.x`
- Tag the release and push to Github
  - For alphas, betas, and release candidates, use lightweight tags. This is
    necessary so that the .devXXXX counter does not reset.
  - For final releases, use annotated tags. This makes the .devXXXX counter reset.
    - `git tag -a v4.0.0 -m v4.0.0`
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
- Update docker-releases repo
  - Create a new branch based of master for major versions.
  - Update the dependencies in [alpine/requirements.txt](https://github.com/mitmproxy/docker-releases/commit/3d6a9989fde068ad0aea257823ac3d7986ff1613#diff-9b7e0eea8ae74688b1ac13ea080549ba)
    * Creating a fresh venv, pip-installing the new wheel in there, and then export all packages:
    * `virtualenv -ppython3.6 venv && source venv/bin/activate && pip install mitmproxy && pip freeze`
  - Tag the commit with the correct version
    * `v2.0.0` for new major versions
    * `v2.0.2` for new patch versions
- Update `latest` tag [here](https://hub.docker.com/r/mitmproxy/mitmproxy/~/settings/automated-builds/)
- Check that the build for this tag succeeds [https://hub.docker.com/r/mitmproxy/mitmproxy/builds/](here)
- If build failed:
  - Fix it and commit
  - `git tag 3.0.2` the new commit
  - `git push origin :refs/tags/3.0.2` to delete the old remote tag
  - `git push --tags` to push the new tag
  - Check the build details page again

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
