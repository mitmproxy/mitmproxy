import SwiftUI
import AppKit

// MARK: - Safe Bundle Module Access

/// Safe accessor for SPM's Bundle.module that doesn't crash in release builds.
/// The auto-generated Bundle.module calls fatalError if the bundle doesn't exist,
/// which happens when the binary is copied to a different app bundle (build-release.sh).
private var safeModuleBundle: Bundle? {
    // Only attempt to access Bundle.module if we're running from .build directory (SPM development)
    let executablePath = Bundle.main.executablePath ?? ""
    guard executablePath.contains(".build/") else {
        return nil
    }

    // Try to find the SPM resource bundle manually without triggering fatalError
    let mainBundlePath = Bundle.main.bundleURL.appendingPathComponent("OximyMac_OximyMac.bundle").path
    if let bundle = Bundle(path: mainBundlePath) {
        return bundle
    }

    // Try the build directory path
    let sourceDir = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().path
    let buildBundlePath = sourceDir + "/.build/arm64-apple-macosx/debug/OximyMac_OximyMac.bundle"
    if let bundle = Bundle(path: buildBundlePath) {
        return bundle
    }

    return nil
}

/// Load Oximy logo from PNG file
struct OximyLogo: View {
    var size: CGFloat = 90

    var body: some View {
        if let image = loadLogoPNG() {
            Image(nsImage: image)
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(width: size, height: size)
        } else {
            // Fallback
            Image(systemName: "square.grid.3x3.fill")
                .font(.system(size: size * 0.7))
                .foregroundColor(.accentColor)
        }
    }
}

/// Resolve path to a resource file
/// Priority order:
/// 1. Bundle.main.resourcePath (release app bundle - must check first!)
/// 2. Bundle.module (SPM development builds only)
/// 3. Source-relative via #filePath (development fallback)
///
/// IMPORTANT: Bundle.module must NOT be checked first because it causes a fatal error
/// when the binary is copied to a new app bundle structure (as done by build-release.sh).
/// The SPM-generated Bundle.module path points to .build/ which doesn't exist in release.
private func resolveResourcePath(_ filename: String, extension ext: String, filePath: String = #filePath) -> String? {
    // Priority 1: App bundle Resources (release builds via build-release.sh)
    // This MUST be checked first because Bundle.module will crash in release builds
    if let bundlePath = Bundle.main.resourcePath {
        let resourcePath = (bundlePath as NSString).appendingPathComponent("\(filename).\(ext)")
        if FileManager.default.fileExists(atPath: resourcePath) {
            return resourcePath
        }
    }

    // Priority 2: SPM development builds - use safe bundle accessor
    // IMPORTANT: Do NOT use Bundle.module directly - it calls fatalError if bundle doesn't exist
    if let moduleBundle = safeModuleBundle,
       let url = moduleBundle.url(forResource: filename, withExtension: ext) {
        return url.path
    }

    // Priority 3: Development - relative to source file
    let sourceDir = URL(fileURLWithPath: filePath).deletingLastPathComponent().deletingLastPathComponent().path
    let devPath = sourceDir + "/Resources/\(filename).\(ext)"
    if FileManager.default.fileExists(atPath: devPath) {
        return devPath
    }

    return nil
}

/// Load logo NSImage from PNG in Resources
/// Uses Oximy.png (the full color logo with orange background)
func loadLogoPNG() -> NSImage? {
    if let path = resolveResourcePath("Oximy", extension: "png") {
        return NSImage(contentsOfFile: path)
    }
    return nil
}

/// Creates an NSImage from the logo for use in menu bar
func createMenuBarIcon() -> NSImage {
    // Use frame.png (transparent background) for menu bar
    if let path = resolveResourcePath("frame", extension: "png"),
       let image = NSImage(contentsOfFile: path) {
        // Set as template so macOS can adapt for light/dark mode
        image.isTemplate = true
        // Ensure correct size for menu bar
        image.size = NSSize(width: 18, height: 18)
        return image
    }

    // Fallback to SF Symbol
    return NSImage(systemSymbolName: "square.grid.3x3.fill", accessibilityDescription: "Oximy")!
}

/// Creates a yellow-tinted menu bar icon for "monitoring paused" state
/// Non-template so the yellow color is preserved
func createMenuBarIconPaused() -> NSImage {
    // Use frame.png (transparent background) for menu bar
    if let path = resolveResourcePath("frame", extension: "png"),
       let originalImage = NSImage(contentsOfFile: path) {

        let size = NSSize(width: 18, height: 18)
        let tintedImage = NSImage(size: size, flipped: false) { rect in
            // Draw the original image scaled to menu bar size
            originalImage.draw(in: rect,
                             from: NSRect(origin: .zero, size: originalImage.size),
                             operation: .sourceOver,
                             fraction: 1.0)

            // Apply yellow tint over the existing pixels
            NSColor.systemYellow.set()
            rect.fill(using: .sourceAtop)

            return true
        }

        // NOT a template - preserve the yellow color
        tintedImage.isTemplate = false
        return tintedImage
    }

    // Fallback to SF Symbol with yellow configuration
    let config = NSImage.SymbolConfiguration(paletteColors: [.systemYellow])
    if let symbol = NSImage(systemSymbolName: "pause.circle.fill", accessibilityDescription: "Oximy Paused")?
        .withSymbolConfiguration(config) {
        symbol.size = NSSize(width: 18, height: 18)
        return symbol
    }

    return NSImage(systemSymbolName: "pause.circle.fill", accessibilityDescription: "Oximy Paused")!
}

#Preview("Logo") {
    OximyLogo(size: 90)
        .padding()
}
