import Foundation

/// Service to detect and read MDM-managed configuration profiles.
///
/// MDM solutions (Jamf, Kandji, Intune, etc.) can deploy configuration profiles
/// that set managed preferences in the app's UserDefaults domain (com.oximy.mac).
/// This service reads those preferences and applies MDM policies.
///
/// Configuration profile keys:
/// - ManagedDeviceToken: Pre-provisioned device API token
/// - ManagedDeviceId: Pre-assigned device identifier
/// - ManagedWorkspaceId: Organization/workspace ID
/// - ManagedWorkspaceName: Display name for workspace
/// - ManagedSetupComplete: Skip all setup UI (Bool)
/// - ManagedEnrollmentComplete: Skip enrollment UI only (Bool)
/// - ManagedCACertInstalled: CA cert deployed via MDM (Bool)
/// - ForceAutoStart: Prevent user from disabling auto-start (Bool)
/// - DisableUserLogout: Hide logout option in UI (Bool)
/// - DisableQuit: Prevent CMD+Q termination (Bool)
/// - APIEndpoint: Custom API URL (String)
@MainActor
final class MDMConfigService: ObservableObject {
    static let shared = MDMConfigService()

    // MARK: - Constants

    /// The app's bundle identifier for reading managed preferences
    private let appIdentifier = "com.oximy.mac" as CFString

    // MARK: - Managed Preference Keys

    /// Keys for MDM-managed preferences (set via configuration profile)
    enum ManagedKey: String {
        // Credentials
        case deviceToken = "ManagedDeviceToken"
        case deviceId = "ManagedDeviceId"
        case workspaceId = "ManagedWorkspaceId"
        case workspaceName = "ManagedWorkspaceName"

        // Setup bypass
        case setupComplete = "ManagedSetupComplete"
        case enrollmentComplete = "ManagedEnrollmentComplete"
        case caCertInstalled = "ManagedCACertInstalled"

        // Lockdown controls
        case forceAutoStart = "ForceAutoStart"
        case disableUserLogout = "DisableUserLogout"
        case disableQuit = "DisableQuit"

        // Configuration
        case apiEndpoint = "APIEndpoint"
        case heartbeatInterval = "HeartbeatInterval"
    }

    // MARK: - Published State

    /// Whether this device is managed by an MDM
    @Published private(set) var isManagedDevice: Bool = false

    /// Timestamp of last config check
    @Published private(set) var lastConfigCheck: Date?

    // MARK: - Initialization

    private init() {
        checkManagedStatus()
    }

    // MARK: - Public Methods

    /// Check if any managed preferences are set and apply configuration
    func checkManagedStatus() {
        // Use CFPreferences to read managed preferences (from /Library/Managed Preferences/)
        // This is required because UserDefaults.standard doesn't automatically read MDM profiles
        let hasToken = getManagedString(for: .deviceToken) != nil
        let hasSetupFlag = getManagedValue(for: .setupComplete) != nil
        let hasEnrollmentFlag = getManagedValue(for: .enrollmentComplete) != nil
        let hasForceAutoStart = getManagedValue(for: .forceAutoStart) != nil

        isManagedDevice = hasToken || hasSetupFlag || hasEnrollmentFlag || hasForceAutoStart
        lastConfigCheck = Date()

        if isManagedDevice {
            print("[MDMConfigService] Managed device detected")
            logManagedConfig()
        } else {
            print("[MDMConfigService] Not a managed device")
        }
    }

    // MARK: - Core Foundation Preference Reading

    /// Read a managed preference value using CFPreferences (reads from /Library/Managed Preferences/)
    private func getManagedValue(for key: ManagedKey) -> Any? {
        let value = CFPreferencesCopyAppValue(key.rawValue as CFString, appIdentifier)
        return value as Any?
    }

    /// Read a managed string preference
    private func getManagedString(for key: ManagedKey) -> String? {
        guard let value = CFPreferencesCopyAppValue(key.rawValue as CFString, appIdentifier) else {
            return nil
        }
        return value as? String
    }

    /// Read a managed boolean preference
    private func getManagedBool(for key: ManagedKey) -> Bool? {
        guard let value = CFPreferencesCopyAppValue(key.rawValue as CFString, appIdentifier) else {
            return nil
        }
        // Handle both Boolean and Number types
        if let boolValue = value as? Bool {
            return boolValue
        }
        if let numValue = value as? NSNumber {
            return numValue.boolValue
        }
        return nil
    }

    /// Read a managed integer preference
    private func getManagedInt(for key: ManagedKey) -> Int? {
        guard let value = CFPreferencesCopyAppValue(key.rawValue as CFString, appIdentifier) else {
            return nil
        }
        if let intValue = value as? Int {
            return intValue
        }
        if let numValue = value as? NSNumber {
            return numValue.intValue
        }
        return nil
    }

    /// Apply managed configuration to app's standard UserDefaults
    /// Call this during app initialization to sync MDM settings
    func applyManagedConfiguration() {
        guard isManagedDevice else { return }

        let defaults = UserDefaults.standard

        // Sync device credentials
        if let token = managedDeviceToken {
            defaults.set(token, forKey: Constants.Defaults.deviceToken)
            print("[MDMConfigService] Applied managed device token")
        }

        if let deviceId = managedDeviceId {
            defaults.set(deviceId, forKey: Constants.Defaults.deviceId)
        }

        if let workspaceId = managedWorkspaceId {
            defaults.set(workspaceId, forKey: Constants.Defaults.workspaceId)
        }

        if let workspaceName = managedWorkspaceName {
            defaults.set(workspaceName, forKey: Constants.Defaults.workspaceName)
        }

        // Sync setup state
        if managedSetupComplete {
            defaults.set(true, forKey: Constants.Defaults.setupComplete)
            print("[MDMConfigService] Applied managed setup complete flag")
        }

        // Sync API configuration
        if let apiEndpoint = managedAPIEndpoint {
            defaults.set(apiEndpoint, forKey: Constants.Defaults.apiEndpoint)
        }

        if let interval = managedHeartbeatInterval {
            defaults.set(interval, forKey: Constants.Defaults.heartbeatInterval)
        }
    }

    // MARK: - Credential Accessors (with 3-tier fallback)

    /// Pre-provisioned device token from MDM
    /// Priority: MDM > remote-state (API) > default (nil)
    var managedDeviceToken: String? {
        if let mdmValue = getManagedString(for: .deviceToken) { return mdmValue }
        if let apiValue = RemoteStateService.shared.appConfig?.managedDeviceToken { return apiValue }
        return nil
    }

    /// Pre-assigned device ID from MDM
    /// Priority: MDM > remote-state (API) > default (nil)
    var managedDeviceId: String? {
        if let mdmValue = getManagedString(for: .deviceId) { return mdmValue }
        if let apiValue = RemoteStateService.shared.appConfig?.managedDeviceId { return apiValue }
        return nil
    }

    /// Organization workspace ID from MDM
    /// Priority: MDM > remote-state (API) > default (nil)
    var managedWorkspaceId: String? {
        if let mdmValue = getManagedString(for: .workspaceId) { return mdmValue }
        if let apiValue = RemoteStateService.shared.appConfig?.managedWorkspaceId { return apiValue }
        return nil
    }

    /// Display name for workspace from MDM
    /// Priority: MDM > remote-state (API) > default (nil)
    var managedWorkspaceName: String? {
        if let mdmValue = getManagedString(for: .workspaceName) { return mdmValue }
        if let apiValue = RemoteStateService.shared.appConfig?.managedWorkspaceName { return apiValue }
        return nil
    }

    // MARK: - Setup Bypass Accessors (with 3-tier fallback)

    /// Skip all setup UI when true (requires device token)
    /// Priority: MDM > remote-state (API) > default
    var managedSetupComplete: Bool {
        if let mdmValue = getManagedBool(for: .setupComplete) { return mdmValue }
        if let apiValue = RemoteStateService.shared.appConfig?.managedSetupComplete { return apiValue }
        return false
    }

    /// Skip enrollment UI only when true (requires device token)
    /// Priority: MDM > remote-state (API) > default
    var managedEnrollmentComplete: Bool {
        if let mdmValue = getManagedBool(for: .enrollmentComplete) { return mdmValue }
        if let apiValue = RemoteStateService.shared.appConfig?.managedEnrollmentComplete { return apiValue }
        return false
    }

    /// CA certificate is already installed via MDM profile
    /// Priority: MDM > remote-state (API) > default
    var managedCACertInstalled: Bool {
        if let mdmValue = getManagedBool(for: .caCertInstalled) { return mdmValue }
        if let apiValue = RemoteStateService.shared.appConfig?.managedCACertInstalled { return apiValue }
        return false
    }

    // MARK: - Lockdown Control Accessors (with 3-tier fallback)

    /// Prevent user from disabling auto-start
    /// Priority: MDM > remote-state (API) > default
    var forceAutoStart: Bool {
        if let mdmValue = getManagedBool(for: .forceAutoStart) { return mdmValue }
        if let apiValue = RemoteStateService.shared.appConfig?.forceAutoStart { return apiValue }
        return false
    }

    /// Hide logout option in UI
    /// Priority: MDM > remote-state (API) > default
    var disableUserLogout: Bool {
        if let mdmValue = getManagedBool(for: .disableUserLogout) { return mdmValue }
        if let apiValue = RemoteStateService.shared.appConfig?.disableUserLogout { return apiValue }
        return false
    }

    /// Prevent CMD+Q from quitting the app
    /// Priority: MDM > remote-state (API) > default
    var disableQuit: Bool {
        if let mdmValue = getManagedBool(for: .disableQuit) { return mdmValue }
        if let apiValue = RemoteStateService.shared.appConfig?.disableQuit { return apiValue }
        return false
    }

    // MARK: - Configuration Accessors (with 3-tier fallback)

    /// Custom API endpoint from MDM
    /// Priority: MDM > remote-state (API) > default (nil)
    var managedAPIEndpoint: String? {
        if let mdmValue = getManagedString(for: .apiEndpoint) { return mdmValue }
        if let apiValue = RemoteStateService.shared.appConfig?.apiEndpoint { return apiValue }
        return nil
    }

    /// Heartbeat interval override from MDM (in seconds)
    /// Priority: MDM > remote-state (API) > default (nil)
    var managedHeartbeatInterval: Int? {
        if let mdmValue = getManagedInt(for: .heartbeatInterval), mdmValue > 0 { return mdmValue }
        if let apiValue = RemoteStateService.shared.appConfig?.heartbeatInterval, apiValue > 0 { return apiValue }
        return nil
    }

    // MARK: - Helper Methods

    /// Whether the app should skip the enrollment phase
    var shouldSkipEnrollment: Bool {
        guard isManagedDevice else { return false }

        // Skip if we have a device token AND enrollment is marked complete
        return managedDeviceToken != nil && (managedEnrollmentComplete || managedSetupComplete)
    }

    /// Whether the app should skip all setup (enrollment + cert + proxy)
    var shouldSkipAllSetup: Bool {
        guard isManagedDevice else { return false }

        // Skip all setup if MDM says so AND we have credentials
        return managedDeviceToken != nil && managedSetupComplete
    }

    /// Log current managed configuration for debugging
    private func logManagedConfig() {
        print("[MDMConfigService] Configuration:")
        print("  - Device Token: \(managedDeviceToken != nil ? "***" : "not set")")
        print("  - Workspace Name: \(managedWorkspaceName ?? "not set")")
        print("  - Setup Complete: \(managedSetupComplete)")
        print("  - Enrollment Complete: \(managedEnrollmentComplete)")
        print("  - CA Cert Installed: \(managedCACertInstalled)")
        print("  - Force Auto-Start: \(forceAutoStart)")
        print("  - Disable Logout: \(disableUserLogout)")
        print("  - Disable Quit: \(disableQuit)")
        print("  - API Endpoint: \(managedAPIEndpoint ?? "default")")
    }
}

// MARK: - MDM Error Types

enum MDMConfigError: LocalizedError {
    case managedByMDM(String)

    var errorDescription: String? {
        switch self {
        case .managedByMDM(let action):
            return "Cannot \(action): This device is managed by your organization."
        }
    }
}
