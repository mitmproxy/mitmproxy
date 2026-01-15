// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "OximyMac",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "OximyMac", targets: ["OximyMac"])
    ],
    dependencies: [
        .package(url: "https://github.com/getsentry/sentry-cocoa", from: "8.20.0"),
        .package(url: "https://github.com/sparkle-project/Sparkle", from: "2.6.0")
    ],
    targets: [
        .executableTarget(
            name: "OximyMac",
            dependencies: [
                .product(name: "Sentry", package: "sentry-cocoa"),
                .product(name: "Sparkle", package: "Sparkle")
            ],
            path: ".",
            exclude: [
                "Info.plist",
                "OximyMac.entitlements",
                "Scripts",
                "Installer",
                "build",
                "project.yml",
                "create-xcode-project.sh",
                "App/Secrets.example.swift",
                "api-docs.md",
                "README.md"
            ],
            sources: [
                "App",
                "Views",
                "Services",
                "Models"
            ],
            resources: [
                // PNG files for logos
                .process("Resources/frame.png"),
                .process("Resources/Oximy.png"),
                // NOTE: python-embed is NOT included here because SPM's COPY_PHASE_STRIP
                // corrupts Python native extensions (.so files) in release builds.
                // The build-release.sh script copies python-embed manually instead.
                // Oximy addon with standalone imports (for bundled Python)
                .copy("Resources/oximy-addon")
            ]
        )
    ]
)
