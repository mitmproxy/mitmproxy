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
        static let setupComplete = "setupComplete"
        static let workspaceName = "workspaceName"
        static let deviceToken = "deviceToken"
        static let autoStartEnabled = "autoStartEnabled"
        static let deviceId = "deviceId"
        static let workspaceId = "workspaceId"
        static let heartbeatInterval = "heartbeatInterval"
        static let eventBatchSize = "eventBatchSize"
        static let eventFlushInterval = "eventFlushInterval"
        static let apiEndpoint = "apiEndpoint"
    }

    // MARK: - API
    static let defaultAPIEndpoint = "https://api.oximy.com/api/v1"

    /// Dev config file path (~/.oximy/dev.json)
    static var devConfigPath: URL {
        oximyDir.appendingPathComponent("dev.json")
    }

    /// Returns API endpoint from dev config if available, otherwise default
    /// Dev config JSON format: {"API_URL": "http://localhost:4000/api/v1", "DEV_MODE": true}
    static var apiEndpoint: String {
        // Check for OXIMY_DEV environment variable first
        if let devEnv = ProcessInfo.processInfo.environment["OXIMY_DEV"],
           ["1", "true", "yes"].contains(devEnv.lowercased()) {
            // Check for custom API URL in environment
            if let apiUrl = ProcessInfo.processInfo.environment["OXIMY_API_URL"] {
                return apiUrl
            }
        }

        // Check for local dev config file
        if let data = try? Data(contentsOf: devConfigPath),
           let config = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let apiUrl = config["API_URL"] as? String {
            return apiUrl
        }

        return defaultAPIEndpoint
    }

    // MARK: - URLs
    static let signUpURL = URL(string: "https://app.oximy.com")!
    static let helpURL = URL(string: "https://docs.oximy.com")!
    static let termsURL = URL(string: "https://oximy.com/terms")!
    static let privacyURL = URL(string: "https://oximy.com/privacy")!
    static let githubURL = URL(string: "https://github.com/oximyhq/sensor")!

    // MARK: - Support Email
    static let supportEmail = "support@oximy.com"

    // MARK: - Sentry
    enum Sentry {
        /// Environment variable name for DSN
        static let dsnEnvKey = "SENTRY_DSN"

        /// Debug send override environment variable
        static let debugSendEnvKey = "SENTRY_DEBUG_SEND"

        /// UserDefaults key for anonymous device ID
        static let deviceIdKey = "sentry_device_id"

        /// Sample rate for performance traces in production (20%)
        static let productionSampleRate: Double = 0.2

        /// App hang timeout threshold (seconds)
        static let appHangTimeout: TimeInterval = 5.0

        /// Max breadcrumbs to retain
        static let maxBreadcrumbs: UInt = 100
    }

    /// Generates a mailto URL with pre-filled subject and system info in the body
    static func supportEmailURL(subject: String = "Oximy Mac Support Request") -> URL? {
        let appVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "Unknown"
        let buildNumber = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "Unknown"
        let osVersion = ProcessInfo.processInfo.operatingSystemVersionString
        let deviceModel = getDeviceModel()

        let body = """


        ---
        Please describe your issue above this line
        ---

        System Information:
        • App Version: \(appVersion) (\(buildNumber))
        • macOS: \(osVersion)
        • Device: \(deviceModel)
        • Oximy Directory: \(oximyDir.path)
        """

        var components = URLComponents()
        components.scheme = "mailto"
        components.path = supportEmail
        components.queryItems = [
            URLQueryItem(name: "subject", value: subject),
            URLQueryItem(name: "body", value: body)
        ]

        return components.url
    }

    private static func getDeviceModel() -> String {
        var size = 0
        sysctlbyname("hw.model", nil, &size, nil, 0)
        var model = [CChar](repeating: 0, count: size)
        sysctlbyname("hw.model", &model, &size, nil, 0)
        return String(cString: model)
    }
}
