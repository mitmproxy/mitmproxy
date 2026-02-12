import Foundation
import Sentry

@MainActor
class SentryService: ObservableObject {
    static let shared = SentryService()

    @Published var isInitialized = false
    @Published var lastError: String?

    private var dsn: String?

    private var isDebugMode: Bool {
        #if DEBUG
        return true
        #else
        return false
        #endif
    }

    private init() {}

    func initialize() {
        let dsn: String? = Secrets.sentryDSN ?? ProcessInfo.processInfo.environment[Constants.Sentry.dsnEnvKey]

        guard let dsn = dsn, !dsn.isEmpty else {
            print("[SentryService] No Sentry DSN configured - Sentry disabled")
            print("[SentryService] Set DSN in App/Secrets.swift or \(Constants.Sentry.dsnEnvKey) env var")
            return
        }

        self.dsn = dsn

        SentrySDK.start { options in
            options.dsn = dsn

            #if DEBUG
            options.environment = "development"
            options.debug = true
            #else
            options.environment = "production"
            options.debug = false
            #endif

            options.sampleRate = 1.0
            options.tracesSampleRate = NSNumber(value: Constants.Sentry.productionSampleRate)

            let appVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.0.0"
            let buildNumber = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "0"
            options.releaseName = "com.oximy.mac@\(appVersion)+\(buildNumber)"

            options.enableAutoBreadcrumbTracking = true
            options.enableAutoSessionTracking = true

            // DISABLED: App acts as a proxy — network tracking could capture
            // proxied request URLs and leak user data to Sentry
            options.enableNetworkTracking = false
            options.enableCaptureFailedRequests = false
            options.enableFileIOTracing = false

            options.attachStacktrace = true
            options.enableAppHangTracking = true
            options.appHangTimeoutInterval = Constants.Sentry.appHangTimeout
            options.sendDefaultPii = false
            options.maxBreadcrumbs = Constants.Sentry.maxBreadcrumbs
        }

        isInitialized = true
        print("[SentryService] Initialized successfully")
        setInitialContext()
    }

    func setUser(workspaceName: String?, deviceId: String? = nil) {
        guard isInitialized else { return }

        let user = User()
        user.username = workspaceName
        user.userId = resolveDeviceId(deviceId)
        SentrySDK.setUser(user)
    }

    func setFullUserContext(
        workspaceName: String?,
        deviceId: String?,
        workspaceId: String?,
        tenantId: String? = nil
    ) {
        guard isInitialized else { return }

        let user = User()
        user.username = workspaceName
        user.userId = resolveDeviceId(deviceId)
        SentrySDK.setUser(user)

        SentrySDK.configureScope { scope in
            if let deviceId = deviceId {
                scope.setTag(value: deviceId, key: "device_id")
            }
            if let workspaceId = workspaceId {
                scope.setTag(value: workspaceId, key: "workspace_id")
            }
            if let workspaceName = workspaceName {
                scope.setTag(value: workspaceName, key: "workspace_name")
            }
            if let tenantId = tenantId {
                scope.setTag(value: tenantId, key: "tenant_id")
            }
            scope.setTag(value: "swift", key: "component")
        }
    }

    func clearUser() {
        guard isInitialized else { return }
        SentrySDK.setUser(nil)
    }

    private func setInitialContext() {
        SentrySDK.configureScope { scope in
            scope.setTag(value: Self.getDeviceModel(), key: "device_model")
            scope.setTag(value: ProcessInfo.processInfo.operatingSystemVersionString, key: "macos_version")

            let appVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "unknown"
            scope.setTag(value: appVersion, key: "app_version")
            scope.setTag(value: "swift", key: "component")
            scope.setTag(value: MDMConfigService.shared.isManagedDevice ? "true" : "false", key: "is_mdm_managed")

            #if arch(arm64)
            scope.setTag(value: "arm64", key: "architecture")
            #else
            scope.setTag(value: "x86_64", key: "architecture")
            #endif
        }
    }

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

    func captureError(_ error: Error, context: [String: Any]? = nil) {
        guard isInitialized else {
            print("[SentryService] Not initialized - error not sent: \(error)")
            return
        }

        SentrySDK.capture(error: error) { scope in
            if let context = context {
                scope.setExtras(context)
            }

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
            } else if let apiError = error as? APIError {
                scope.setTag(value: "api", key: "error_category")
                scope.setTag(value: apiError.errorCode, key: "error_code")
            }
        }

        lastError = error.localizedDescription
        print("[SentryService] Captured error: \(error.localizedDescription)")
    }

    func captureMessage(_ message: String, level: SentryLevel = .info) {
        guard isInitialized else { return }

        SentrySDK.capture(message: message) { scope in
            scope.setLevel(level)
        }
    }

    func addBreadcrumb(type: String, category: String, message: String = "", data: [String: Any]? = nil, level: SentryLevel = .info) {
        guard isInitialized else { return }

        let crumb = Breadcrumb()
        crumb.type = type
        crumb.category = category
        crumb.message = message
        crumb.data = data
        crumb.level = level
        SentrySDK.addBreadcrumb(crumb)
    }

    func addNavigationBreadcrumb(from: String, to: String) {
        addBreadcrumb(type: "navigation", category: "ui.navigation", data: ["from": from, "to": to])
    }

    func addUserActionBreadcrumb(action: String, target: String? = nil) {
        addBreadcrumb(
            type: "user",
            category: "ui.action",
            message: action,
            data: target.map { ["target": $0] }
        )
    }

    func addStateBreadcrumb(category: String, message: String, data: [String: Any]? = nil) {
        addBreadcrumb(type: "info", category: category, message: message, data: data)
    }

    func addErrorBreadcrumb(service: String, error: String) {
        addBreadcrumb(type: "error", category: service, message: error, level: .error)
    }

    func startTransaction(name: String, operation: String) -> Span? {
        guard isInitialized else { return nil }
        return SentrySDK.startTransaction(name: name, operation: operation)
    }

    func startSpan(parent: Span, operation: String, description: String) -> Span {
        return parent.startChild(operation: operation, description: description)
    }

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

    func appWillTerminate() {
        guard isInitialized else { return }

        addStateBreadcrumb(
            category: "app.lifecycle",
            message: "App terminating"
        )

        SentrySDK.flush(timeout: 2.0)
    }

    // Resolve device ID: provided > stored > new UUID
    private func resolveDeviceId(_ provided: String?) -> String {
        if let provided = provided {
            return provided
        }
        if let existingId = UserDefaults.standard.string(forKey: Constants.Sentry.deviceIdKey) {
            return existingId
        }
        let newId = UUID().uuidString
        UserDefaults.standard.set(newId, forKey: Constants.Sentry.deviceIdKey)
        return newId
    }

    private static func getDeviceModel() -> String {
        var size = 0
        sysctlbyname("hw.model", nil, &size, nil, 0)
        var model = [CChar](repeating: 0, count: size)
        sysctlbyname("hw.model", &model, &size, nil, 0)
        return String(cString: model)
    }
}

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
        case .managedByMDM:
            return "LAUNCH_MDM_BLOCKED"
        }
    }
}

extension APIError {
    var errorCode: String {
        switch self {
        case .networkUnavailable:
            return "API_NETWORK_UNAVAILABLE"
        case .invalidEnrollmentCode:
            return "API_INVALID_CODE"
        case .enrollmentExpired:
            return "API_ENROLLMENT_EXPIRED"
        case .unauthorized:
            return "API_UNAUTHORIZED"
        case .deviceNotFound:
            return "API_DEVICE_NOT_FOUND"
        case .conflict:
            return "API_CONFLICT"
        case .serverError:
            return "API_SERVER_ERROR"
        case .encodingError:
            return "API_ENCODING_ERROR"
        case .decodingError:
            return "API_DECODING_ERROR"
        case .rateLimited:
            return "API_RATE_LIMITED"
        }
    }
}
