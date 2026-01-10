import Foundation

enum Constants {
    // MARK: - Networking
    static let preferredPort = 1030  // Founding date
    static let portSearchRange = 100  // Search ±100 from preferred
    static let listenHost = "127.0.0.1"

    // MARK: - Directories
    static var oximyDir: URL {
        FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".oximy")
    }

    static var tracesDir: URL {
        oximyDir.appendingPathComponent("traces")
    }

    static var logsDir: URL {
        oximyDir.appendingPathComponent("logs")
    }

    static var bundleCachePath: URL {
        oximyDir.appendingPathComponent("bundle_cache.json")
    }

    // MARK: - Certificates (named for mitmproxy compatibility)
    static var caKeyPath: URL {
        oximyDir.appendingPathComponent("mitmproxy-ca.pem")
    }

    static var caCertPath: URL {
        oximyDir.appendingPathComponent("mitmproxy-ca-cert.pem")
    }

    // MARK: - CA Branding
    static let caCommonName = "Oximy CA"
    static let caOrganization = "Oximy Inc"
    static let caCountry = "US"
    static let caValidityDays = 3650  // 10 years

    // MARK: - App Info
    static let appName = "Oximy"
    static let bundleIdentifier = "com.oximy.mac"
    static let helperBundleIdentifier = "com.oximy.mac.helper"

    // MARK: - UserDefaults Keys
    enum Defaults {
        static let onboardingComplete = "onboardingComplete"
        static let workspaceName = "workspaceName"
        static let deviceToken = "deviceToken"
        static let autoStartEnabled = "autoStartEnabled"
    }

    // MARK: - URLs
    static let signUpURL = URL(string: "https://app.oximy.com")!
    static let helpURL = URL(string: "https://oximy.com/help")!
    static let supportURL = URL(string: "https://oximy.com/support")!
    static let termsURL = URL(string: "https://oximy.com/terms")!
    static let privacyURL = URL(string: "https://oximy.com/privacy")!
    static let githubURL = URL(string: "https://github.com/oximy")!
}
