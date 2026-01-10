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
    targets: [
        .executableTarget(
            name: "OximyMac",
            path: ".",
            exclude: [
                "Info.plist",
                "OximyMac.entitlements",
                "Scripts",
                "Installer",
                "build",
                "project.yml",
                "create-xcode-project.sh"
            ],
            sources: [
                "App",
                "Views",
                "Services"
            ],
            resources: [
                // PNG files for logos
                .process("Resources/frame.png"),
                .process("Resources/Oximy.png"),
                // Bundled Python + mitmproxy (preserve directory structure)
                .copy("Resources/python-embed"),
                // Oximy addon
                .copy("Resources/oximy-addon")
            ]
        )
    ]
)
