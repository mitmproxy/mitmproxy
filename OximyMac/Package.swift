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
        .package(url: "https://github.com/getsentry/sentry-cocoa", from: "8.20.0")
    ],
    targets: [
        .executableTarget(
            name: "OximyMac",
            dependencies: [
                .product(name: "Sentry", package: "sentry-cocoa")
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
                // Bundled Python + mitmproxy (preserve directory structure)
                .copy("Resources/python-embed"),
                // Oximy addon with standalone imports (for bundled Python)
                .copy("Resources/oximy-addon")
            ]
        )
    ]
)
