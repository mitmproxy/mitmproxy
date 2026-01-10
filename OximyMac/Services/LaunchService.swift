import Foundation
import ServiceManagement

/// Service to manage auto-start on login
@MainActor
class LaunchService: ObservableObject {
    static let shared = LaunchService()

    @Published var isEnabled: Bool = false
    @Published var lastError: String?

    private init() {
        checkStatus()
    }

    // MARK: - Status

    /// Check if auto-start is currently enabled
    func checkStatus() {
        if #available(macOS 13.0, *) {
            isEnabled = SMAppService.mainApp.status == .enabled
        } else {
            // Fallback for older macOS: check if LaunchAgent plist exists
            isEnabled = FileManager.default.fileExists(atPath: launchAgentPath)
        }

        print("[LaunchService] Auto-start is \(isEnabled ? "enabled" : "disabled")")
    }

    // MARK: - Enable/Disable

    /// Enable auto-start on login
    func enable() throws {
        if #available(macOS 13.0, *) {
            do {
                try SMAppService.mainApp.register()
                isEnabled = true
                lastError = nil
                print("[LaunchService] Enabled auto-start via SMAppService")
            } catch {
                lastError = error.localizedDescription
                throw LaunchServiceError.registrationFailed(error.localizedDescription)
            }
        } else {
            // Fallback: create LaunchAgent plist
            try createLaunchAgentPlist()
            isEnabled = true
            lastError = nil
            print("[LaunchService] Enabled auto-start via LaunchAgent plist")
        }

        // Save preference
        UserDefaults.standard.set(true, forKey: Constants.Defaults.autoStartEnabled)
    }

    /// Disable auto-start on login
    func disable() throws {
        if #available(macOS 13.0, *) {
            do {
                try SMAppService.mainApp.unregister()
                isEnabled = false
                lastError = nil
                print("[LaunchService] Disabled auto-start via SMAppService")
            } catch {
                lastError = error.localizedDescription
                throw LaunchServiceError.unregistrationFailed(error.localizedDescription)
            }
        } else {
            // Fallback: remove LaunchAgent plist
            try removeLaunchAgentPlist()
            isEnabled = false
            lastError = nil
            print("[LaunchService] Disabled auto-start via LaunchAgent plist removal")
        }

        // Save preference
        UserDefaults.standard.set(false, forKey: Constants.Defaults.autoStartEnabled)
    }

    /// Toggle auto-start
    func toggle() throws {
        if isEnabled {
            try disable()
        } else {
            try enable()
        }
    }

    // MARK: - LaunchAgent (Fallback for macOS < 13)

    private var launchAgentPath: String {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        return "\(home)/Library/LaunchAgents/com.oximy.agent.plist"
    }

    private func createLaunchAgentPlist() throws {
        let plistContent = """
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>com.oximy.agent</string>
            <key>ProgramArguments</key>
            <array>
                <string>/Applications/Oximy.app/Contents/MacOS/Oximy</string>
            </array>
            <key>RunAtLoad</key>
            <true/>
            <key>KeepAlive</key>
            <false/>
        </dict>
        </plist>
        """

        // Ensure LaunchAgents directory exists
        let launchAgentsDir = (launchAgentPath as NSString).deletingLastPathComponent
        try FileManager.default.createDirectory(
            atPath: launchAgentsDir,
            withIntermediateDirectories: true
        )

        // Write plist
        try plistContent.write(toFile: launchAgentPath, atomically: true, encoding: .utf8)
    }

    private func removeLaunchAgentPlist() throws {
        let fm = FileManager.default
        if fm.fileExists(atPath: launchAgentPath) {
            try fm.removeItem(atPath: launchAgentPath)
        }
    }

    // MARK: - Status Description

    var statusDescription: String {
        if #available(macOS 13.0, *) {
            switch SMAppService.mainApp.status {
            case .enabled:
                return "Enabled"
            case .notRegistered:
                return "Not registered"
            case .requiresApproval:
                return "Requires approval in System Settings"
            case .notFound:
                return "App not found"
            @unknown default:
                return "Unknown"
            }
        } else {
            return isEnabled ? "Enabled (LaunchAgent)" : "Disabled"
        }
    }
}

// MARK: - Errors

enum LaunchServiceError: LocalizedError {
    case registrationFailed(String)
    case unregistrationFailed(String)

    var errorDescription: String? {
        switch self {
        case .registrationFailed(let reason):
            return "Failed to enable auto-start: \(reason)"
        case .unregistrationFailed(let reason):
            return "Failed to disable auto-start: \(reason)"
        }
    }
}
