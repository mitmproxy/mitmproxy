import SwiftUI
import AppKit

// Development path for resources (used when running via swift build)
private let devResourcesPath = "/Users/namanambavi/Desktop/Oximy/Code/mitmproxy/OximyMac/Resources"

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

/// Load logo NSImage from PNG in Resources
/// Uses Oximy.png (the full color logo with orange background)
func loadLogoPNG() -> NSImage? {
    // Try Bundle.module first (SPM way)
    // Use Oximy.png which is the full color logo
    if let url = Bundle.module.url(forResource: "Oximy", withExtension: "png") {
        return NSImage(contentsOf: url)
    }

    // Development fallback: check source directory
    let devPath = "\(devResourcesPath)/Oximy.png"
    if FileManager.default.fileExists(atPath: devPath) {
        return NSImage(contentsOfFile: devPath)
    }

    return nil
}

/// Creates an NSImage from the logo for use in menu bar
func createMenuBarIcon() -> NSImage {
    let image: NSImage?

    // Use frame.png (transparent background) for menu bar
    if let url = Bundle.module.url(forResource: "frame", withExtension: "png") {
        image = NSImage(contentsOf: url)
    } else {
        // Development fallback
        let framePath = "\(devResourcesPath)/frame.png"
        image = NSImage(contentsOfFile: framePath)
    }

    if let image = image {
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
