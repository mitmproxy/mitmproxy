- This project uses uv. Always use `uv run pytest` and don't run pytest directly.
- To run all tests: `uv run tox`.
- When adding new source files, additionally run: `uv run tox -e individual_coverage -- FILENAME`.

## Project Structure & Deployment

All addon changes should be made in the root `mitmproxy/addons/` directory. This is the source of truth for addon code.

After making changes, you need to build and copy the bundle to the respective platform apps:

### macOS
```bash
cd OximyMac && make build
```
This syncs the addon from `mitmproxy/addons/oximy/` to `OximyMac/Resources/oximy-addon/` (converting imports automatically) and builds the Swift app.

Other useful commands:
- `make sync` - Just sync addon files without building
- `make run` - Sync, build, and run
- `make release` - Build release version
- `make dmg` - Build release DMG for distribution

### Windows
```powershell
cd OximyWindows/scripts && .\build.ps1
```
This copies the addon from `mitmproxy/addons/oximy/` to `OximyWindows/src/OximyWindows/Resources/oximy-addon/`, fixes imports, and builds the .NET app.

Options:
- `.\build.ps1 -Release` - Build release version
- `.\build.ps1 -Clean` - Clean before building
- `.\build.ps1 -CreateInstaller` - Also create installer
- `.\build.ps1 -CreateVelopack -Version "1.0.0"` - Create Velopack release

**Important:** Always make changes in `mitmproxy/addons/oximy/` first, then run the appropriate build command to deploy to platform-specific app bundles. Both build systems automatically sync the addon and fix imports for standalone use.
