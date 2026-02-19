import Foundation
import Cocoa
import UserNotifications
import os.log

@MainActor
final class AppBlockingService: ObservableObject {
    static let shared = AppBlockingService()

    private let logger = Logger(subsystem: "com.oximy.sensor", category: "AppBlocking")

    /// Bundle IDs that have been warned this session (don't re-warn)
    private var warnedApps: Set<String> = []

    /// Currently showing block/warn windows (prevent duplicates)
    private var activeWindows: [String: NSWindow] = [:]

    /// Workspace observers for app launch
    private var launchObserver: NSObjectProtocol?
    private var rulesObserver: NSObjectProtocol?

    /// Current enforcement rules (filtered to app-type with macBundleId)
    private var appRules: [String: EnforcementRule] = [:]  // keyed by macBundleId lowercased

    private init() {}

    func start() {
        logger.info("AppBlockingService starting")

        // Load initial rules
        updateRules(RemoteStateService.shared.enforcementRules)

        // Listen for rule changes
        rulesObserver = NotificationCenter.default.addObserver(
            forName: .enforcementRulesChanged,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            guard let rules = notification.object as? [EnforcementRule] else { return }
            Task { @MainActor in
                self?.updateRules(rules)
            }
        }

        // Listen for app launches
        launchObserver = NSWorkspace.shared.notificationCenter.addObserver(
            forName: NSWorkspace.didLaunchApplicationNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            guard let app = notification.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication else { return }
            Task { @MainActor in
                self?.handleAppLaunch(app)
            }
        }

        // Check already-running apps against current rules
        scanRunningApps()
    }

    func stop() {
        logger.info("AppBlockingService stopping")
        if let obs = launchObserver {
            NSWorkspace.shared.notificationCenter.removeObserver(obs)
            launchObserver = nil
        }
        if let obs = rulesObserver {
            NotificationCenter.default.removeObserver(obs)
            rulesObserver = nil
        }
        // Close any active windows
        for (_, window) in activeWindows {
            window.close()
        }
        activeWindows.removeAll()
    }

    // MARK: - Rules Management

    private func updateRules(_ rules: [EnforcementRule]) {
        let newRules: [String: EnforcementRule] = Dictionary(
            uniqueKeysWithValues: rules
                .filter { $0.toolType == "app" && $0.macBundleId != nil }
                .map { ($0.macBundleId!.lowercased(), $0) }
        )

        let oldRules = appRules
        appRules = newRules

        logger.info("Updated enforcement rules: \(newRules.count) app rules")

        // If rules changed, scan running apps for newly blocked apps
        if oldRules != newRules {
            scanRunningApps()
        }
    }

    /// Check if this device is exempt from a rule (approved access request)
    private func isDeviceExempt(rule: EnforcementRule) -> Bool {
        guard let exemptIds = rule.exemptDeviceIds, !exemptIds.isEmpty else { return false }
        guard let hwId = APIClient.getHardwareUUID() else { return false }
        return exemptIds.contains(hwId)
    }

    private func scanRunningApps() {
        let ownBundleId = Bundle.main.bundleIdentifier?.lowercased() ?? ""

        for app in NSWorkspace.shared.runningApplications {
            guard let bundleId = app.bundleIdentifier?.lowercased() else { continue }
            guard bundleId != ownBundleId else { continue }  // Never block ourselves

            if let rule = appRules[bundleId], rule.mode == "blocked", !isDeviceExempt(rule: rule) {
                enforceBlock(app: app, rule: rule)
            }
        }
    }

    // MARK: - App Launch Handling

    private func handleAppLaunch(_ app: NSRunningApplication) {
        guard let bundleId = app.bundleIdentifier?.lowercased() else { return }

        // Never block our own app
        let ownBundleId = Bundle.main.bundleIdentifier?.lowercased() ?? ""
        guard bundleId != ownBundleId else { return }

        guard let rule = appRules[bundleId] else { return }

        // Skip enforcement if this device has an approved access request
        if isDeviceExempt(rule: rule) {
            logger.info("Device exempt from enforcement for \(rule.displayName)")
            return
        }

        logger.info("Enforcement triggered for \(rule.displayName) (mode: \(rule.mode))")

        switch rule.mode {
        case "blocked":
            enforceBlock(app: app, rule: rule)
        case "warn":
            enforceWarn(app: app, rule: rule)
        case "flagged":
            enforceFlagged(app: app, rule: rule)
        default:
            break
        }
    }

    // MARK: - Enforcement Actions

    private func enforceBlock(app: NSRunningApplication, rule: EnforcementRule) {
        let bundleId = app.bundleIdentifier?.lowercased() ?? ""
        let appIcon = app.icon

        // Terminate the app
        let terminated = app.forceTerminate()
        if terminated {
            logger.info("Blocked and terminated: \(rule.displayName)")
            OximyLogger.shared.log(.BLOCK_APP_001, "App blocked and terminated", data: [
                "bundleId": bundleId,
                "name": rule.displayName
            ])
        } else {
            logger.error("Failed to terminate: \(rule.displayName)")
            OximyLogger.shared.log(.BLOCK_APP_002, "App block failed - could not terminate", data: [
                "bundleId": bundleId,
                "name": rule.displayName
            ])
        }

        // Show block window
        showBlockWindow(rule: rule, appIcon: appIcon)
    }

    private func enforceWarn(app: NSRunningApplication, rule: EnforcementRule) {
        let bundleId = app.bundleIdentifier?.lowercased() ?? ""

        // Only warn once per session
        guard !warnedApps.contains(bundleId) else { return }
        warnedApps.insert(bundleId)

        logger.info("Warning shown for: \(rule.displayName)")
        OximyLogger.shared.log(.BLOCK_WARN_001, "App warn shown", data: [
            "bundleId": bundleId,
            "name": rule.displayName
        ])

        // Show warn window
        showWarnWindow(rule: rule, appIcon: app.icon)
    }

    private func enforceFlagged(app: NSRunningApplication, rule: EnforcementRule) {
        let bundleId = app.bundleIdentifier?.lowercased() ?? ""

        // Only flag once per session
        guard !warnedApps.contains("flagged_\(bundleId)") else { return }
        warnedApps.insert("flagged_\(bundleId)")

        logger.info("Flagged notification for: \(rule.displayName)")
        OximyLogger.shared.log(.BLOCK_FLAG_001, "App flagged notification shown", data: [
            "bundleId": bundleId,
            "name": rule.displayName
        ])

        // Show notification via UNUserNotificationCenter
        let content = UNMutableNotificationContent()
        content.title = "\(rule.displayName) — Conditions Apply"
        content.body = rule.conditions ?? rule.message ?? "This application has usage conditions set by your organization."
        content.sound = .default

        let request = UNNotificationRequest(
            identifier: "flagged_\(bundleId)",
            content: content,
            trigger: nil
        )

        UNUserNotificationCenter.current().add(request) { error in
            if let error = error {
                self.logger.error("Failed to show flagged notification: \(error.localizedDescription)")
            }
        }
    }

    // MARK: - Window Management

    private func showBlockWindow(rule: EnforcementRule, appIcon: NSImage?) {
        let key = "block_\(rule.macBundleId?.lowercased() ?? rule.toolId)"

        // Don't show duplicate windows
        if activeWindows[key] != nil { return }

        let window = createEnforcementWindow(
            rule: rule,
            mode: .blocked,
            appIcon: appIcon,
            onDismiss: { [weak self] in
                self?.activeWindows.removeValue(forKey: key)
            },
            onRequestAccess: { [weak self] reason in
                self?.submitAccessRequest(rule: rule, reason: reason)
            }
        )

        activeWindows[key] = window
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func showWarnWindow(rule: EnforcementRule, appIcon: NSImage?) {
        let key = "warn_\(rule.macBundleId?.lowercased() ?? rule.toolId)"

        if activeWindows[key] != nil { return }

        let window = createEnforcementWindow(
            rule: rule,
            mode: .warn,
            appIcon: appIcon,
            onDismiss: { [weak self] in
                self?.activeWindows.removeValue(forKey: key)
            },
            onRequestAccess: nil
        )

        activeWindows[key] = window
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    // MARK: - Window Factory

    enum EnforcementMode {
        case blocked
        case warn
    }

    private func createEnforcementWindow(
        rule: EnforcementRule,
        mode: EnforcementMode,
        appIcon: NSImage?,
        onDismiss: @escaping () -> Void,
        onRequestAccess: ((String) -> Void)?
    ) -> NSWindow {
        let width: CGFloat = 360
        let height: CGFloat = mode == .blocked ? 310 : 260

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: width, height: height),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )

        window.center()
        window.level = .floating
        window.isReleasedWhenClosed = false
        window.title = mode == .blocked ? "Application Blocked" : "Usage Advisory"

        let contentView = NSView(frame: NSRect(x: 0, y: 0, width: width, height: height))

        // Layout from top (NSView y=0 is bottom, y=height is top)
        var cursorY = height - 28.0  // 28px top padding

        // App icon
        let iconSize: CGFloat = 44
        cursorY -= iconSize
        let iconView = NSImageView(frame: NSRect(
            x: (width - iconSize) / 2,
            y: cursorY,
            width: iconSize,
            height: iconSize
        ))
        if let icon = appIcon ?? NSWorkspace.shared.icon(forFile: "/Applications") as NSImage? {
            icon.size = NSSize(width: iconSize, height: iconSize)
            iconView.image = icon
        }
        iconView.imageScaling = .scaleProportionallyUpOrDown
        contentView.addSubview(iconView)

        // App name
        cursorY -= 22  // 10px gap + 12px visual
        let nameLabel = NSTextField(labelWithString: rule.displayName)
        nameLabel.font = .systemFont(ofSize: 15, weight: .semibold)
        nameLabel.alignment = .center
        nameLabel.frame = NSRect(x: 24, y: cursorY, width: width - 48, height: 20)
        contentView.addSubview(nameLabel)

        // Status
        cursorY -= 20  // 4px gap
        let statusText = mode == .blocked ? "Blocked by your organization" : "Usage advisory"
        let statusLabel = NSTextField(labelWithString: statusText)
        statusLabel.font = .systemFont(ofSize: 11, weight: .medium)
        statusLabel.textColor = mode == .blocked ? .systemRed : .systemOrange
        statusLabel.alignment = .center
        statusLabel.frame = NSRect(x: 24, y: cursorY, width: width - 48, height: 16)
        contentView.addSubview(statusLabel)

        // Message
        cursorY -= 54  // 12px gap + 42px text area
        let message = rule.message ?? (mode == .blocked
            ? "This application has been restricted by your organization."
            : "This application is not recommended for use.")
        let messageLabel = NSTextField(wrappingLabelWithString: message)
        messageLabel.font = .systemFont(ofSize: 12)
        messageLabel.textColor = .secondaryLabelColor
        messageLabel.alignment = .center
        messageLabel.frame = NSRect(x: 32, y: cursorY, width: width - 64, height: 42)
        contentView.addSubview(messageLabel)

        // Store callbacks on window
        objc_setAssociatedObject(window, &AssociatedKeys.onDismiss, onDismiss, .OBJC_ASSOCIATION_RETAIN)

        if mode == .blocked {
            objc_setAssociatedObject(window, &AssociatedKeys.onRequestAccess, onRequestAccess, .OBJC_ASSOCIATION_RETAIN)

            // Buttons side-by-side at bottom
            let btnWidth: CGFloat = 130
            let btnGap: CGFloat = 12
            let totalBtnWidth = btnWidth * 2 + btnGap
            let btnX = (width - totalBtnWidth) / 2
            let btnY: CGFloat = 28

            let dismissBtn = NSButton(title: "Dismiss", target: window, action: #selector(NSWindow.enforcementHandleDismiss))
            dismissBtn.bezelStyle = .rounded
            dismissBtn.frame = NSRect(x: btnX, y: btnY, width: btnWidth, height: 28)
            contentView.addSubview(dismissBtn)

            let requestBtn = NSButton(title: "Request Access", target: window, action: #selector(NSWindow.enforcementHandleRequestAccess))
            requestBtn.bezelStyle = .rounded
            requestBtn.keyEquivalent = "\r"  // Default button (highlighted)
            requestBtn.frame = NSRect(x: btnX + btnWidth + btnGap, y: btnY, width: btnWidth, height: 28)
            contentView.addSubview(requestBtn)
        } else {
            let btnWidth: CGFloat = 140
            let understandBtn = NSButton(title: "I Understand", target: window, action: #selector(NSWindow.enforcementHandleDismiss))
            understandBtn.bezelStyle = .rounded
            understandBtn.keyEquivalent = "\r"
            understandBtn.frame = NSRect(x: (width - btnWidth) / 2, y: 28, width: btnWidth, height: 28)
            contentView.addSubview(understandBtn)
        }

        window.contentView = contentView
        return window
    }

    // MARK: - Access Request

    private func submitAccessRequest(rule: EnforcementRule, reason: String) {
        Task {
            do {
                try await APIClient.shared.requestAccess(
                    toolId: rule.toolId,
                    toolType: rule.toolType,
                    displayName: rule.displayName,
                    reason: reason
                )
                OximyLogger.shared.log(.BLOCK_REQ_001, "Access request submitted", data: [
                    "toolId": rule.toolId,
                    "name": rule.displayName
                ])
                logger.info("Access request submitted for \(rule.displayName)")

                // Show success feedback
                let successAlert = NSAlert()
                successAlert.messageText = "Request Submitted"
                successAlert.informativeText = "Your access request for \(rule.displayName) has been sent to your administrator."
                successAlert.alertStyle = .informational
                successAlert.addButton(withTitle: "OK")
                successAlert.runModal()
            } catch {
                logger.error("Failed to submit access request: \(error.localizedDescription)")

                // Show error feedback
                let errorAlert = NSAlert()
                errorAlert.messageText = "Request Failed"
                errorAlert.informativeText = "Could not submit your access request. Please try again or contact your administrator.\n\n\(error.localizedDescription)"
                errorAlert.alertStyle = .warning
                errorAlert.addButton(withTitle: "OK")
                errorAlert.runModal()
            }
        }
    }
}

// MARK: - Associated Object Keys

private struct AssociatedKeys {
    static var onDismiss = "enforcementOnDismiss"
    static var onRequestAccess = "enforcementOnRequestAccess"
}

// MARK: - NSWindow Extensions for Button Actions

extension NSWindow {
    @objc func enforcementHandleDismiss() {
        if let onDismiss = objc_getAssociatedObject(self, &AssociatedKeys.onDismiss) as? () -> Void {
            onDismiss()
        }
        self.close()
    }

    @objc func enforcementHandleRequestAccess() {
        let alert = NSAlert()
        alert.messageText = "Request Access"
        alert.informativeText = "Provide a reason for your access request:"
        alert.addButton(withTitle: "Submit")
        alert.addButton(withTitle: "Cancel")

        let input = NSTextField(frame: NSRect(x: 0, y: 0, width: 260, height: 24))
        input.placeholderString = "I need this for..."
        alert.accessoryView = input

        let response = alert.runModal()
        if response == .alertFirstButtonReturn {
            let reason = input.stringValue.isEmpty ? "Access requested" : input.stringValue
            if let onRequestAccess = objc_getAssociatedObject(self, &AssociatedKeys.onRequestAccess) as? (String) -> Void {
                onRequestAccess(reason)
            }
        }

        if let onDismiss = objc_getAssociatedObject(self, &AssociatedKeys.onDismiss) as? () -> Void {
            onDismiss()
        }
        self.close()
    }
}
