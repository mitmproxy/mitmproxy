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
    private func getManagedBool(for key: ManagedKey) -> Bool {
        guard let value = CFPreferencesCopyAppValue(key.rawValue as CFString, appIdentifier) else {
            return false
        }
        // Handle both Boolean and Number types
        if let boolValue = value as? Bool {
            return boolValue
        }
        if let numValue = value as? NSNumber {
            return numValue.boolValue
        }
        return false
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

    // MARK: - Credential Accessors

    /// Pre-provisioned device token from MDM
    var managedDeviceToken: String? {
        getManagedString(for: .deviceToken)
    }

    /// Pre-assigned device ID from MDM
    var managedDeviceId: String? {
        getManagedString(for: .deviceId)
    }

    /// Organization workspace ID from MDM
    var managedWorkspaceId: String? {
        getManagedString(for: .workspaceId)
    }

    /// Display name for workspace from MDM
    var managedWorkspaceName: String? {
        getManagedString(for: .workspaceName)
    }

    // MARK: - Setup Bypass Accessors

    /// Skip all setup UI when true (requires device token)
    var managedSetupComplete: Bool {
        getManagedBool(for: .setupComplete)
    }

    /// Skip enrollment UI only when true (requires device token)
    var managedEnrollmentComplete: Bool {
        getManagedBool(for: .enrollmentComplete)
    }

    /// CA certificate is already installed via MDM profile
    var managedCACertInstalled: Bool {
        getManagedBool(for: .caCertInstalled)
    }

    // MARK: - Lockdown Control Accessors

    /// Prevent user from disabling auto-start
    var forceAutoStart: Bool {
        getManagedBool(for: .forceAutoStart)
    }

    /// Hide logout option in UI
    var disableUserLogout: Bool {
        getManagedBool(for: .disableUserLogout)
    }

    /// Prevent CMD+Q from quitting the app
    var disableQuit: Bool {
        getManagedBool(for: .disableQuit)
    }

    // MARK: - Configuration Accessors

    /// Custom API endpoint from MDM
    var managedAPIEndpoint: String? {
        getManagedString(for: .apiEndpoint)
    }

    /// Heartbeat interval override from MDM (in seconds)
    var managedHeartbeatInterval: Int? {
        guard let value = getManagedInt(for: .heartbeatInterval), value > 0 else {
            return nil
        }
        return value
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
