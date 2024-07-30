# Release Checklist

1. Check if `mitmproxy-rs` needs a new release.
2. Make sure that `CHANGELOG.md` is up-to-date with all entries in the "Unreleased" section.
3. Invoke the [release workflow](https://github.com/mitmproxy/mitmproxy/actions/workflows/release.yml) from the GitHub UI.
4. The spawned workflow runs will require manual confirmation on GitHub which you need to approve twice: 
   https://github.com/mitmproxy/mitmproxy/actions
5. Once everything has been deployed, update the website.
6. Verify that the front-page download links for all platforms are working.

### GitHub Releases

- CI will automatically create a GitHub release:  
  https://github.com/mitmproxy/mitmproxy/releases

### PyPi

- CI will automatically push a wheel to GitHub:  
  https://pypi.python.org/pypi/mitmproxy

### Docker

- CI will automatically push images to Docker Hub:  
  https://hub.docker.com/r/mitmproxy/mitmproxy/tags/

### Docs

- CI will automatically update the stable docs and create an archive version:  
  `https://docs.mitmproxy.org/archive/vMAJOR/`

### Download Server

- CI will automatically push binaries to our download S3 bucket:  
  https://mitmproxy.org/downloads/

### Microsoft Store

- CI will automatically update the Microsoft Store version:  
  https://apps.microsoft.com/store/detail/mitmproxy/9NWNDLQMNZD7
- There is a review process, binaries may take a day to show up.

### Homebrew

- The Homebrew maintainers are typically very fast and detect our new relese
  within a day.
- If you feel the need, you can run this from a macOS machine:
  `brew bump-cask-pr mitmproxy`

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
