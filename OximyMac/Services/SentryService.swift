import Foundation
import Sentry

/// Service to manage Sentry SDK for crash reporting, error tracking, and performance monitoring
@MainActor
class SentryService: ObservableObject {
    static let shared = SentryService()

    // MARK: - Published Properties

    @Published var isInitialized = false
    @Published var lastError: String?

    // MARK: - Configuration

    private var dsn: String?

    private var isDebugMode: Bool {
        #if DEBUG
        return true
        #else
        return false
        #endif
    }

    // MARK: - Initialization

    private init() {}

    /// Initialize Sentry SDK with configuration
    /// Call this FIRST in applicationDidFinishLaunching, before any other setup
    func initialize() {
        // Get DSN: prefer Secrets.swift, fall back to environment variable
        let dsn: String? = Secrets.sentryDSN ?? ProcessInfo.processInfo.environment[Constants.Sentry.dsnEnvKey]

        guard let dsn = dsn, !dsn.isEmpty else {
            print("[SentryService] No Sentry DSN configured - Sentry disabled")
            print("[SentryService] Set DSN in App/Secrets.swift or \(Constants.Sentry.dsnEnvKey) env var")
            return
        }

        self.dsn = dsn

        SentrySDK.start { options in
            options.dsn = dsn

            // Environment configuration
            #if DEBUG
            options.environment = "development"
            options.debug = true
            options.enableTracing = true
            // Don't send events in debug mode by default
            options.beforeSend = { event in
                // Allow sending in debug if explicitly enabled
                if ProcessInfo.processInfo.environment[Constants.Sentry.debugSendEnvKey] == "1" {
                    return event
                }
                print("[SentryService] DEBUG: Would send event: \(event.eventId.sentryIdString)")
                return nil
            }
            #else
            options.environment = "production"
            options.debug = false
            options.enableTracing = true
            options.tracesSampleRate = NSNumber(value: Constants.Sentry.productionSampleRate)
            #endif

            // Release version
            let appVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.0.0"
            let buildNumber = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "0"
            options.releaseName = "com.oximy.mac@\(appVersion)+\(buildNumber)"

            // Enable automatic breadcrumbs
            options.enableAutoBreadcrumbTracking = true
            options.enableAutoSessionTracking = true
            options.enableNetworkTracking = true
            options.enableFileIOTracing = true

            // Crash handling
            options.attachStacktrace = true
            options.enableCaptureFailedRequests = true

            // Performance
            options.enableAppHangTracking = true
            options.appHangTimeoutInterval = Constants.Sentry.appHangTimeout

            // Privacy - don't send PII by default
            options.sendDefaultPii = false

            // Max breadcrumbs
            options.maxBreadcrumbs = Constants.Sentry.maxBreadcrumbs
        }

        isInitialized = true
        print("[SentryService] Initialized successfully")

        // Set initial context
        setInitialContext()
    }

    // MARK: - User Context

    /// Set user context information
    func setUser(workspaceName: String?, deviceId: String? = nil) {
        guard isInitialized else { return }

        let user = User()
        user.username = workspaceName

        // Generate anonymous device ID if not provided
        if let deviceId = deviceId {
            user.userId = deviceId
        } else if let existingId = UserDefaults.standard.string(forKey: Constants.Sentry.deviceIdKey) {
            user.userId = existingId
        } else {
            let newId = UUID().uuidString
            UserDefaults.standard.set(newId, forKey: Constants.Sentry.deviceIdKey)
            user.userId = newId
        }

        SentrySDK.setUser(user)
    }

    /// Clear user context (on logout)
    func clearUser() {
        guard isInitialized else { return }
        SentrySDK.setUser(nil)
    }

    /// Set initial device and app context
    private func setInitialContext() {
        SentrySDK.configureScope { scope in
            // Device info
            scope.setTag(value: Self.getDeviceModel(), key: "device_model")
            scope.setTag(value: ProcessInfo.processInfo.operatingSystemVersionString, key: "macos_version")

            // App context
            let appVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "unknown"
            scope.setTag(value: appVersion, key: "app_version")

            // Architecture
            #if arch(arm64)
            scope.setTag(value: "arm64", key: "architecture")
            #else
            scope.setTag(value: "x86_64", key: "architecture")
            #endif
        }
    }

    /// Update context with current app state
    func updateContext(phase: String, proxyEnabled: Bool, port: Int?) {
        guard isInitialized else { return }

        SentrySDK.configureScope { scope in
            scope.setTag(value: phase, key: "app_phase")
            scope.setTag(value: proxyEnabled ? "enabled" : "disabled", key: "proxy_status")
            if let port = port {
                scope.setTag(value: String(port), key: "proxy_port")
            }
        }
    }

    // MARK: - Error Capture

    /// Capture a LocalizedError with full context
    func captureError(_ error: Error, context: [String: Any]? = nil) {
        guard isInitialized else {
            print("[SentryService] Not initialized - error not sent: \(error)")
            return
        }

        SentrySDK.capture(error: error) { scope in
            // Add error-specific context
            if let context = context {
                scope.setExtras(context)
            }

            // Categorize by error type
            if let mitmError = error as? MITMError {
                scope.setTag(value: "mitm", key: "error_category")
                scope.setTag(value: mitmError.errorCode, key: "error_code")
            } else if let proxyError = error as? ProxyError {
                scope.setTag(value: "proxy", key: "error_category")
                scope.setTag(value: proxyError.errorCode, key: "error_code")
            } else if let certError = error as? CertificateError {
                scope.setTag(value: "certificate", key: "error_category")
                scope.setTag(value: certError.errorCode, key: "error_code")
            } else if let launchError = error as? LaunchServiceError {
                scope.setTag(value: "launch", key: "error_category")
                scope.setTag(value: launchError.errorCode, key: "error_code")
            }
        }

        lastError = error.localizedDescription
        print("[SentryService] Captured error: \(error.localizedDescription)")
    }

    /// Capture a message (non-error event)
    func captureMessage(_ message: String, level: SentryLevel = .info) {
        guard isInitialized else { return }

        SentrySDK.capture(message: message) { scope in
            scope.setLevel(level)
        }
    }

    // MARK: - Breadcrumbs

    /// Add a navigation breadcrumb
    func addNavigationBreadcrumb(from: String, to: String) {
        guard isInitialized else { return }

        let crumb = Breadcrumb()
        crumb.type = "navigation"
        crumb.category = "ui.navigation"
        crumb.data = ["from": from, "to": to]
        crumb.level = .info
        SentrySDK.addBreadcrumb(crumb)
    }

    /// Add a user action breadcrumb
    func addUserActionBreadcrumb(action: String, target: String? = nil) {
        guard isInitialized else { return }

        let crumb = Breadcrumb()
        crumb.type = "user"
        crumb.category = "ui.action"
        crumb.message = action
        if let target = target {
            crumb.data = ["target": target]
        }
        crumb.level = .info
        SentrySDK.addBreadcrumb(crumb)
    }

    /// Add a state change breadcrumb
    func addStateBreadcrumb(category: String, message: String, data: [String: Any]? = nil) {
        guard isInitialized else { return }

        let crumb = Breadcrumb()
        crumb.type = "info"
        crumb.category = category
        crumb.message = message
        crumb.data = data
        crumb.level = .info
        SentrySDK.addBreadcrumb(crumb)
    }

    /// Add an error breadcrumb (for non-fatal errors)
    func addErrorBreadcrumb(service: String, error: String) {
        guard isInitialized else { return }

        let crumb = Breadcrumb()
        crumb.type = "error"
        crumb.category = service
        crumb.message = error
        crumb.level = .error
        SentrySDK.addBreadcrumb(crumb)
    }

    // MARK: - Performance Monitoring

    /// Start a transaction for a multi-step operation
    func startTransaction(name: String, operation: String) -> Span? {
        guard isInitialized else { return nil }
        return SentrySDK.startTransaction(name: name, operation: operation)
    }

    /// Start a child span within a transaction
    func startSpan(parent: Span, operation: String, description: String) -> Span {
        return parent.startChild(operation: operation, description: description)
    }

    /// Convenience: Measure an async operation
    func measureAsync<T>(
        name: String,
        operation: String,
        block: () async throws -> T
    ) async throws -> T {
        guard isInitialized else {
            return try await block()
        }

        let transaction = SentrySDK.startTransaction(name: name, operation: operation)
        do {
            let result = try await block()
            transaction.finish(status: .ok)
            return result
        } catch {
            transaction.finish(status: .internalError)
            throw error
        }
    }

    // MARK: - App Lifecycle

    /// Call when app is terminating (for clean shutdown tracking)
    func appWillTerminate() {
        guard isInitialized else { return }

        addStateBreadcrumb(
            category: "app.lifecycle",
            message: "App terminating",
            data: nil
        )

        // Flush pending events
        SentrySDK.flush(timeout: 2.0)
    }

    // MARK: - Helpers

    private static func getDeviceModel() -> String {
        var size = 0
        sysctlbyname("hw.model", nil, &size, nil, 0)
        var model = [CChar](repeating: 0, count: size)
        sysctlbyname("hw.model", &model, &size, nil, 0)
        return String(cString: model)
    }
}

// MARK: - Error Code Extensions

extension MITMError {
    var errorCode: String {
        switch self {
        case .noAvailablePort:
            return "MITM_NO_PORT"
        case .addonNotFound:
            return "MITM_ADDON_NOT_FOUND"
        case .mitmdumpNotFound:
            return "MITM_DUMP_NOT_FOUND"
        case .processStartFailed:
            return "MITM_START_FAILED"
        case .portNotListening:
            return "MITM_PORT_NOT_LISTENING"
        }
    }
}

extension ProxyError {
    var errorCode: String {
        switch self {
        case .commandFailed:
            return "PROXY_CMD_FAILED"
        case .serviceNotFound:
            return "PROXY_SERVICE_NOT_FOUND"
        }
    }
}

extension CertificateError {
    var errorCode: String {
        switch self {
        case .generationFailed:
            return "CERT_GEN_FAILED"
        case .pkcs12Failed:
            return "CERT_PKCS12_FAILED"
        case .keychainAddFailed:
            return "CERT_KEYCHAIN_ADD_FAILED"
        case .trustFailed:
            return "CERT_TRUST_FAILED"
        case .removalFailed:
            return "CERT_REMOVAL_FAILED"
        }
    }
}

extension LaunchServiceError {
    var errorCode: String {
        switch self {
        case .registrationFailed:
            return "LAUNCH_REG_FAILED"
        case .unregistrationFailed:
            return "LAUNCH_UNREG_FAILED"
        }
    }
}
