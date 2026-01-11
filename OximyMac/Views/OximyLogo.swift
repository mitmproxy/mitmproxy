import SwiftUI
import AppKit

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

/// Resolve path to a resource file using the same priority as MITMService
/// 1. Bundle.module (SPM builds)
/// 2. Bundle.main.resourcePath (Xcode release builds)
/// 3. Source-relative via #filePath (development)
private func resolveResourcePath(_ filename: String, extension ext: String, filePath: String = #filePath) -> String? {
    // Priority 1: Bundle.module (SPM builds)
    if let url = Bundle.module.url(forResource: filename, withExtension: ext) {
        return url.path
    }

    // Priority 2: App bundle Resources (Xcode release builds)
    if let bundlePath = Bundle.main.resourcePath {
        let resourcePath = (bundlePath as NSString).appendingPathComponent("\(filename).\(ext)")
        if FileManager.default.fileExists(atPath: resourcePath) {
            return resourcePath
        }
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

#Preview("Logo") {
    OximyLogo(size: 90)
        .padding()
}
