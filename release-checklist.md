# Release Checklist

## Test

  - Create the source distributions, make sure the output is sensible:  
    `./release/build.py release`  
    All source distributions can be found in `./dist`.

  - Test the source distributions:  
    `./release/build.py test`  
    This creates a new virtualenv in `../venv.mitmproxy-release` and installs the distributions from `./dist` into it.

## Release

  - Verify that repositories are in a clean state:
    `./release/build.py git status`

  - Update the version number in `version.py` for all projects:  
    `./release/build.py set-version 0.13`

  - Ensure that the website style assets have been compiled for production, and synced to the docs.

  - Render the docs, update CONTRIBUTORS file:  
    `./release/build.py docs contributors`
  
  - Make version bump commit for all projects, tag and push it:
    `./release/build.py git commit -am "bump version"`
    `./release/build.py git tag v0.13`  
    `./release/build.py git push --tags`

  - Recreate the source distributions with updated version information:  
    `./release/build.py sdist`

  - Build the OSX binaries
    - Follow instructions in osx-binaries
    - Move to download dir:  
      `mv ./tmp/osx-mitmproxy-VERSION.tar.gz ~/mitmproxy/www.mitmproxy.org/src/download`

  - Move all source distributions from `./dist` to the server:  
    `mv ./dist/* ~/mitmproxy/www.mitmproxy.org/src/download`

  - Upload distributions in `./dist` to PyPI:  
    `./release/build.py upload`  
    You can test with [testpypi.python.org](https://testpypi.python.org/pypi) by passing `--repository test`.
    ([more info](https://tom-christie.github.io/articles/pypi/))

  - Now bump the version number to be ready for the next cycle:

    **TODO**: We just shipped 0.12 - do we bump to 0.12.1 or 0.13 now? 
    We should probably just leave it as-is and only bump once we actually do the next release.
    
    Also, we need a release policy. I propose the following:
      - By default, every release is a new minor (`0.x`) release and it will be pushed for all three projects.
      - Only if an emergency bugfix is needed, we push a new `0.x.y` bugfix release for a single project.
        This matches with what we do in `setup.py`: `"netlib>=%s, <%s" % (version.MINORVERSION, version.NEXT_MINORVERSION)`