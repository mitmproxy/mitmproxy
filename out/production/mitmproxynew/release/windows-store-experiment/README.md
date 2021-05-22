# Mitmproxy on the Windows Store

@mhils experimented with bringing mitmproxy to the Window Store using the Desktop Bridge. This would replace our current InstallBuilder setup and allow for clean installs and - more importantly - automatic updates.

## Advantages

- Automatic updates
- Clean installs
- Very simple setup on our end
- Possibility to roll out experimental releases to a subset of users

## Disadvantages

- No support for mitmproxy. That only runs under WSL. Making WSL nicer is a complementary effort.
- "Your developer account doesn’t have permission to submit apps converted with the Desktop Bridge at this time." (requested)
- New releases need to be submitted manually (Submission API is in preview).

## Notes

We do not want to force anyone to use this, we would of course keep our portable binaries (and, of course, WSL).
