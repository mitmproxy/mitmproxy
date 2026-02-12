import SwiftUI
import AppKit

extension Notification.Name {
    static let quitApp = Notification.Name("quitApp")
    static let handleAuthURL = Notification.Name("handleAuthURL")
}

@main
struct OximyApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        // Settings scene with empty content - this prevents SwiftUI from creating
        // any default windows. The actual UI is managed via AppDelegate.
        // Note: Settings windows are only shown when user clicks Preferences menu,
        // which we don't expose in our menu bar app.
        Settings {
            Text("Settings are managed in the popover")
                .frame(width: 200, height: 50)
        }
        // Hidden WindowGroup for URL handling - catches oximy:// deep links
        // and prevents SwiftUI from launching a new app instance
        WindowGroup("URLHandler") {
            Color.clear
                .frame(width: 0, height: 0)
                .onOpenURL { url in
                    NotificationCenter.default.post(name: .handleAuthURL, object: url)
                }
                .onAppear {
                    // Close this window immediately - we only need it for URL handling
                    DispatchQueue.main.async {
                        for window in NSApplication.shared.windows {
                            if window.title == "URLHandler" {
                                window.close()
                            }
                        }
                    }
                }
        }
        .handlesExternalEvents(matching: Set(arrayLiteral: "oximy"))
        .defaultSize(width: 0, height: 0)
    }

    init() {
        // Close any windows that might be open on launch
        DispatchQueue.main.async {
            for window in NSApplication.shared.windows {
                if window.title.contains("Settings") || window.title.isEmpty || window.title == "URLHandler" {
                    window.close()
                }
            }
        }
    }
}

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {

    // MARK: - Properties

    let appState = AppState()

    private var statusItem: NSStatusItem!
    private var popover: NSPopover!
    private var remoteStateObserver: NSObjectProtocol?
    private var mainMenuQuitItem: NSMenuItem?
    private var isShowingQuitBlockedAlert = false

    // MARK: - App Lifecycle

    func applicationDidFinishLaunching(_ notification: Notification) {
        // CRITICAL: Export env vars BEFORE initializing Sentry
        // setenv() is not thread-safe — must run before Sentry spawns background threads
        if let dsn = Secrets.sentryDSN {
            setenv("SENTRY_DSN", dsn, 1)
        }
        #if DEBUG
        setenv("OXIMY_ENV", "development", 1)
        #else
        setenv("OXIMY_ENV", "production", 1)
        #endif
        setenv("OXIMY_SESSION_ID", OximyLogger.shared.sessionId, 1)

        // Initialize Sentry (now env vars are already set)
        SentryService.shared.initialize()

        // CRITICAL: Clean up any orphaned proxy settings from a previous crash
        // This MUST run before any UI loads to restore internet connectivity
        ProxyService.shared.cleanupOrphanedProxy()

        // Startup snapshot event
        let appVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "unknown"
        let buildNumber = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "unknown"
        OximyLogger.shared.log(.APP_INIT_001, "Application launched", data: [
            "app_version": appVersion,
            "build_number": buildNumber,
            "macos_version": ProcessInfo.processInfo.operatingSystemVersionString,
            "architecture": {
                #if arch(arm64)
                return "arm64"
                #else
                return "x86_64"
                #endif
            }(),
            "is_mdm_managed": MDMConfigService.shared.isManagedDevice,
            "phase": appState.phase.rawValue,
            "cert_generated": CertificateService.shared.isCAGenerated,
            "cert_installed": CertificateService.shared.isCAInstalled,
            "has_device_token": UserDefaults.standard.string(forKey: Constants.Defaults.deviceToken) != nil,
            "network_connected": NetworkMonitor.shared.isConnected,
            "session_id": OximyLogger.shared.sessionId
        ])

        // Hide from dock - menu bar only app
        NSApp.setActivationPolicy(.accessory)

        // Setup menu bar
        setupStatusItem()
        setupPopover()
        setupMainMenu()

        // Update Sentry context with initial state
        SentryService.shared.updateContext(
            phase: appState.phase.rawValue,
            proxyEnabled: ProxyService.shared.isProxyEnabled,
            port: MITMService.shared.currentPort
        )

        // Set user context if logged in
        if appState.isLoggedIn {
            SentryService.shared.setFullUserContext(
                workspaceName: appState.workspaceName,
                deviceId: UserDefaults.standard.string(forKey: Constants.Defaults.deviceId),
                workspaceId: UserDefaults.standard.string(forKey: Constants.Defaults.workspaceId)
            )
        }

        // Listen for quit notification
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleQuitApp),
            name: .quitApp,
            object: nil
        )

        // Listen for network changes
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleNetworkChange),
            name: .networkChanged,
            object: nil
        )

        // Listen for mitmproxy failures
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleMitmproxyFailed),
            name: .mitmproxyFailed,
            object: nil
        )

        // Listen for auth failures (401 after retries exhausted)
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleAuthFailure),
            name: .authenticationFailed,
            object: nil
        )

        // Listen for URL auth callbacks (from SwiftUI onOpenURL)
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleAuthURLNotification(_:)),
            name: .handleAuthURL,
            object: nil
        )

        // Start remote state monitoring (reads Python addon's state file)
        RemoteStateService.shared.start()

        // Observe sensor state changes for menu bar icon
        remoteStateObserver = NotificationCenter.default.addObserver(
            forName: .sensorEnabledChanged,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.updateMenuBarIcon()
            }
        }

        // Start network monitoring
        NetworkMonitor.shared.startMonitoring()

        // Auto-show popover on first launch (enrollment or setup - not ready)
        // This ensures users see the UI immediately, not just the menu bar icon
        print("[OximyApp] Initial phase: \(appState.phase.rawValue)")
        if appState.phase != .ready {
            print("[OximyApp] Phase is not ready, will show popover after delay")
            // Use a slightly longer delay to ensure menu bar is fully set up
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
                guard let self = self else {
                    print("[OximyApp] Self was deallocated before showing popover")
                    return
                }
                print("[OximyApp] Showing popover now, statusItem.button exists: \(self.statusItem.button != nil)")
                self.showPopoverAndFocus()
            }
        } else {
            print("[OximyApp] Phase is ready, not auto-showing popover")
        }
    }

    private func showPopover() {
        guard let button = statusItem.button else { return }
        popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
        makePopoverOpaque()
    }

    /// Remove visual effect view from popover to prevent desktop bleeding through
    private func makePopoverOpaque() {
        guard let popoverWindow = popover.contentViewController?.view.window else { return }
        // Find and disable the visual effect view in the popover
        if let frameView = popoverWindow.contentView?.superview {
            for subview in frameView.subviews {
                if let visualEffectView = subview as? NSVisualEffectView {
                    visualEffectView.state = .inactive
                    visualEffectView.material = .windowBackground
                }
            }
        }
        popoverWindow.isOpaque = true
        popoverWindow.backgroundColor = NSColor.windowBackgroundColor
    }

    /// Show popover and ensure it's focused (for first launch)
    private func showPopoverAndFocus() {
        guard let button = statusItem.button else {
            print("[OximyApp] showPopoverAndFocus: statusItem.button is nil!")
            return
        }

        print("[OximyApp] showPopoverAndFocus: button bounds = \(button.bounds)")

        // Show the popover
        popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
        makePopoverOpaque()
        print("[OximyApp] showPopoverAndFocus: popover.isShown = \(popover.isShown)")

        // Make the popover window key and bring to front
        if let popoverWindow = popover.contentViewController?.view.window {
            popoverWindow.makeKeyAndOrderFront(nil)
            popoverWindow.level = .floating  // Ensure it's above other windows
            print("[OximyApp] showPopoverAndFocus: popover window set to floating level")
        } else {
            print("[OximyApp] showPopoverAndFocus: could not get popover window")
        }

        // Also activate the app to ensure keyboard focus works
        NSApp.activate(ignoringOtherApps: true)
        print("[OximyApp] showPopoverAndFocus: app activated")
    }

    @objc private func handleQuitApp() {
        // Close any open windows first
        popover.performClose(nil)

        // Then quit
        quitApp()
    }

    @objc private func handleNetworkChange() {
        print("[OximyApp] Network changed - checking if proxy needs reconfiguration")

        Task {
            // Only reconfigure if we're ready
            guard appState.phase == .ready else {
                print("[OximyApp] Skipping proxy reconfiguration (not in ready state)")
                return
            }

            // FAIL-OPEN: Get port from mitmproxy if running, otherwise use default
            // This ensures we can re-enable proxy even if state is inconsistent
            var port = MITMService.shared.currentPort

            if port == nil {
                // FAIL-OPEN: mitmproxy might have crashed - try to restart it
                if !MITMService.shared.isRunning {
                    print("[OximyApp] FAIL-OPEN: mitmproxy not running after network change - attempting restart")
                    // Reset restart counter so we get fresh attempts
                    MITMService.shared.resetRestartCounter()
                    do {
                        try await MITMService.shared.start()
                        port = MITMService.shared.currentPort
                        print("[OximyApp] FAIL-OPEN: mitmproxy restarted on port \(port ?? 0)")
                    } catch {
                        print("[OximyApp] FAIL-OPEN: mitmproxy restart failed: \(error)")
                        // Continue without proxy rather than blocking user
                        return
                    }
                }
            }

            guard let port = port else {
                print("[OximyApp] No proxy port available - skipping reconfiguration")
                return
            }

            do {
                // Re-enable proxy on all current network services
                // FAIL-OPEN: Uses local state, no API dependency
                try await ProxyService.shared.enableProxy(port: port)
                print("[OximyApp] Proxy reconfigured successfully for new network on port \(port)")
            } catch {
                print("[OximyApp] Failed to reconfigure proxy: \(error)")
                OximyLogger.shared.log(.NET_FAIL_301, "Proxy reconfiguration failed after network change", data: [
                    "error": error.localizedDescription
                ])
                // FAIL-OPEN: Log error but don't block user's internet
                appState.connectionStatus = .error("Network change failed")
            }
        }
    }

    @objc private func handleMitmproxyFailed() {
        print("[OximyApp] mitmproxy failed permanently")
        OximyLogger.shared.log(.MITM_RETRY_401, "mitmproxy failed permanently, max restarts exceeded")
        appState.connectionStatus = .error("Proxy service failed")
    }

    @objc private func handleAuthFailure() {
        print("[OximyApp] Authentication failed after retries - returning to enrollment")
        appState.handleAuthFailure()

        // Show the popover so user sees the enrollment screen
        showPopover()
    }

    // MARK: - URL Handling (for oximy:// deep links)

    @objc private func handleAuthURLNotification(_ notification: Notification) {
        if let url = notification.object as? URL {
            print("[OximyApp] Received URL via notification: \(url)")
            handleAuthCallback(url: url)
        }
    }

    func application(_ application: NSApplication, open urls: [URL]) {
        for url in urls {
            handleAuthCallback(url: url)
        }
    }

    private func handleAuthCallback(url: URL) {
        print("[OximyApp] Received URL: \(url)")

        // Parse: oximy://auth/callback?token=xxx&state=xxx&device_id=xxx
        // Note: workspace_name and workspace_id are NOT in the callback URL.
        // They are fetched from the API using the device token.
        guard url.scheme == "oximy",
              url.host == "auth",
              url.path == "/callback" else {
            print("[OximyApp] URL doesn't match auth callback pattern")
            return
        }

        let components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        let queryItems = components?.queryItems ?? []

        // Extract parameters (only token, state, and device_id expected)
        let token = queryItems.first { $0.name == "token" }?.value
        let state = queryItems.first { $0.name == "state" }?.value
        let deviceId = queryItems.first { $0.name == "device_id" }?.value

        // Validate state matches what we stored (CSRF protection)
        let storedState = UserDefaults.standard.string(forKey: Constants.Defaults.authState)
        guard state == storedState else {
            print("[OximyApp] State mismatch - stored: \(storedState ?? "nil"), received: \(state ?? "nil")")
            OximyLogger.shared.log(.AUTH_FAIL_302, "Auth callback state mismatch")
            return
        }

        // Clear stored state
        UserDefaults.standard.removeObject(forKey: Constants.Defaults.authState)

        // Validate we have a token
        guard let token = token else {
            print("[OximyApp] No token in callback URL")
            OximyLogger.shared.log(.AUTH_FAIL_303, "Auth callback missing token")
            return
        }

        print("[OximyApp] Auth callback parameters:")
        print("[OximyApp]   token: \(token.prefix(20))...")
        print("[OximyApp]   device_id: \(deviceId ?? "not provided")")

        // Fetch workspace info from API using the token
        Task {
            do {
                print("[OximyApp] Fetching device info from API...")
                let deviceInfo = try await APIClient.shared.fetchDeviceInfo(token: token)

                print("[OximyApp] Device info received:")
                print("[OximyApp]   workspaceName: \(deviceInfo.workspaceName)")
                print("[OximyApp]   workspaceId: \(deviceInfo.workspaceId)")
                print("[OximyApp]   deviceId: \(deviceInfo.deviceId)")

                // Use deviceId from API response (authoritative), fallback to URL if API doesn't return it
                let finalDeviceId = deviceInfo.deviceId

                appState.login(
                    workspaceName: deviceInfo.workspaceName,
                    deviceToken: token,
                    deviceId: finalDeviceId,
                    workspaceId: deviceInfo.workspaceId
                )

                appState.completeEnrollment()

                SentryService.shared.addStateBreadcrumb(
                    category: "enrollment",
                    message: "Device enrolled via browser auth",
                    data: [
                        "deviceId": finalDeviceId,
                        "workspaceId": deviceInfo.workspaceId,
                        "workspaceName": deviceInfo.workspaceName
                    ]
                )

                print("[OximyApp] Auth callback processed successfully")

                // Show the popover so user sees they're logged in
                showPopover()

            } catch {
                print("[OximyApp] Failed to fetch device info: \(error)")

                // Fallback: Log in with minimal info but warn
                // The heartbeat service will eventually get the workspace info
                print("[OximyApp] Falling back to minimal login (device_id from URL: \(deviceId ?? "nil"))")

                appState.login(
                    workspaceName: "Loading...",
                    deviceToken: token,
                    deviceId: deviceId,
                    workspaceId: nil
                )

                appState.completeEnrollment()

                SentryService.shared.addErrorBreadcrumb(
                    service: "enrollment",
                    error: "Failed to fetch device info after browser auth: \(error.localizedDescription)"
                )

                showPopover()
            }
        }
    }

    private func setupMainMenu() {
        let mainMenu = NSMenu()

        // App menu (Oximy)
        let appMenu = NSMenu()
        appMenu.addItem(NSMenuItem(title: "About Oximy", action: #selector(showAbout), keyEquivalent: ""))
        appMenu.addItem(NSMenuItem.separator())

        let quitItem = NSMenuItem(title: "Quit Oximy", action: #selector(quitApp), keyEquivalent: "")
        if MDMConfigService.shared.disableQuit {
            quitItem.isEnabled = false
        }
        mainMenuQuitItem = quitItem
        appMenu.addItem(quitItem)

        let appMenuItem = NSMenuItem()
        appMenuItem.submenu = appMenu
        mainMenu.addItem(appMenuItem)

        appMenu.delegate = self
        NSApp.mainMenu = mainMenu
    }

    @objc private func showAbout() {
        NSApp.orderFrontStandardAboutPanel(nil)
    }

    private var allowQuit = false

    @objc private func quitApp() {
        if MDMConfigService.shared.disableQuit {
            print("[OximyApp] Quit blocked by policy (DisableQuit)")
            showQuitBlockedAlert()
            return
        }

        print("[OximyApp] Quit requested - setting allowQuit=true")
        allowQuit = true

        DispatchQueue.main.async {
            NSApp.terminate(nil)
        }
    }

    private func showQuitBlockedAlert() {
        guard !isShowingQuitBlockedAlert else { return }
        isShowingQuitBlockedAlert = true

        let alert = NSAlert()
        alert.messageText = "Quit is disabled"
        if let itSupport = RemoteStateService.shared.itSupport, !itSupport.isEmpty {
            alert.informativeText = "Quitting Oximy has been disabled by your organization.\n\nContact your IT administrator: \(itSupport)"
        } else {
            alert.informativeText = "Quitting Oximy has been disabled by your organization.\n\nContact your IT administrator for more information."
        }
        alert.alertStyle = .informational
        alert.addButton(withTitle: "OK")
        alert.runModal()

        isShowingQuitBlockedAlert = false
    }

    // Block CMD+Q unless explicitly allowed via quitApp()
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        print("[OximyApp] applicationShouldTerminate called, allowQuit=\(allowQuit)")

        if MDMConfigService.shared.disableQuit {
            print("[OximyApp] Termination blocked by policy")
            showQuitBlockedAlert()
            return .terminateCancel
        }

        if allowQuit {
            print("[OximyApp] Allowing termination")
            return .terminateNow
        }
        // CMD+Q pressed - close popover but don't quit
        if popover.isShown {
            popover.performClose(nil)
        }
        return .terminateCancel
    }

    func applicationWillTerminate(_ notification: Notification) {
        // Remove all notification observers to prevent leaks
        NotificationCenter.default.removeObserver(self, name: .quitApp, object: nil)
        NotificationCenter.default.removeObserver(self, name: .networkChanged, object: nil)
        NotificationCenter.default.removeObserver(self, name: .mitmproxyFailed, object: nil)
        NotificationCenter.default.removeObserver(self, name: .authenticationFailed, object: nil)
        NotificationCenter.default.removeObserver(self, name: .handleAuthURL, object: nil)

        // Remove remote state observer
        if let observer = remoteStateObserver {
            NotificationCenter.default.removeObserver(observer)
            remoteStateObserver = nil
        }

        // Remove global event monitor
        if let monitor = clickMonitor {
            NSEvent.removeMonitor(monitor)
            clickMonitor = nil
        }

        // Stop network monitoring
        NetworkMonitor.shared.stopMonitoring()

        // Stop remote state monitoring
        RemoteStateService.shared.stop()

        // Stop API services
        HeartbeatService.shared.stop()
        SyncService.shared.flushSync()

        // Log termination BEFORE Sentry flush
        OximyLogger.shared.log(.APP_STOP_001, "App terminating")
        OximyLogger.shared.close()

        // Notify Sentry of clean shutdown
        SentryService.shared.appWillTerminate()

        // CRITICAL: Cleanup proxy and mitmproxy so user doesn't lose internet
        // Use synchronous version to ensure it completes before app exits
        ProxyService.shared.disableProxySync()
        MITMService.shared.stop()

        print("[OximyApp] Cleanup complete - proxy disabled, mitmproxy stopped")
    }

    // MARK: - Menu Bar Setup

    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)

        if let button = statusItem.button {
            // Use Oximy logo
            button.image = createMenuBarIcon()
            button.action = #selector(handleStatusItemClick)
            button.target = self
            button.sendAction(on: [.leftMouseUp, .rightMouseUp])
        }
    }

    @objc private func handleStatusItemClick(_ sender: NSStatusBarButton) {
        let event = NSApp.currentEvent

        if event?.type == .rightMouseUp {
            // Right-click: show context menu
            showStatusItemMenu()
        } else {
            // Left-click: toggle popover
            togglePopover()
        }
    }

    private func showStatusItemMenu() {
        let menu = NSMenu()

        // Status indicator
        let statusItem = NSMenuItem(title: statusText, action: nil, keyEquivalent: "")
        statusItem.isEnabled = false
        menu.addItem(statusItem)

        menu.addItem(NSMenuItem.separator())

        let quitItem = NSMenuItem(title: "Quit Oximy", action: #selector(quitApp), keyEquivalent: "")
        if MDMConfigService.shared.disableQuit {
            quitItem.isEnabled = false
            quitItem.toolTip = "Quit is disabled by your organization"
        }
        menu.addItem(quitItem)

        self.statusItem.menu = menu
        self.statusItem.button?.performClick(nil)
        self.statusItem.menu = nil  // Remove menu so left-click works normally again
    }

    private var statusText: String {
        if !RemoteStateService.shared.sensorEnabled {
            return "○ Monitoring Paused"
        } else if RemoteStateService.shared.proxyActive {
            return "● Monitoring Active"
        } else if appState.phase == .setup {
            return "○ Setup Required"
        } else {
            return "○ Starting..."
        }
    }

    private func updateMenuBarIcon() {
        guard let button = statusItem.button else { return }
        if RemoteStateService.shared.sensorEnabled {
            button.image = createMenuBarIcon()
        } else {
            button.image = createMenuBarIconPaused()
        }
    }

    private var clickMonitor: Any?

    private func setupPopover() {
        // Clean up any existing monitor before creating a new one (prevents accumulation)
        if let existingMonitor = clickMonitor {
            NSEvent.removeMonitor(existingMonitor)
            clickMonitor = nil
        }

        popover = NSPopover()
        popover.contentSize = NSSize(width: 340, height: 420)
        // Use .applicationDefined so clicking buttons inside doesn't close the popover
        popover.behavior = .applicationDefined
        popover.animates = true

        // Set the main content view - using MainView from Views/MainView.swift
        let contentView = MainView()
            .environmentObject(appState)

        let hostingController = NSHostingController(rootView: contentView)
        // Make the popover background opaque to prevent desktop bleeding through
        hostingController.view.wantsLayer = true
        hostingController.view.layer?.backgroundColor = NSColor.windowBackgroundColor.cgColor
        popover.contentViewController = hostingController

        // Set up event monitor to close popover when clicking outside
        clickMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown]) { [weak self] _ in
            guard let self = self, self.popover.isShown else { return }
            self.popover.performClose(nil)
        }
    }

    // MARK: - Actions

    @objc private func togglePopover() {
        guard let button = statusItem.button else { return }

        if popover.isShown {
            popover.performClose(nil)
        } else {
            popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
            makePopoverOpaque()

            // Ensure the popover window becomes key
            popover.contentViewController?.view.window?.makeKey()
        }
    }
}

// MARK: - NSMenuDelegate

extension AppDelegate: NSMenuDelegate {
    func menuNeedsUpdate(_ menu: NSMenu) {
        guard let quitItem = mainMenuQuitItem else { return }
        quitItem.isEnabled = !MDMConfigService.shared.disableQuit
    }
}
