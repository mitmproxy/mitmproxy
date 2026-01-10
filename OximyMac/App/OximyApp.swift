import SwiftUI
import AppKit

extension Notification.Name {
    static let openSettings = Notification.Name("openSettings")
    static let quitApp = Notification.Name("quitApp")
    static let logout = Notification.Name("logout")
}

@main
struct OximyApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        // Settings window (opened via gear icon)
        Settings {
            SettingsView()
                .environmentObject(appDelegate.appState)
        }
    }
}

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {

    // MARK: - Properties

    let appState = AppState()

    private var statusItem: NSStatusItem!
    private var popover: NSPopover!
    private var settingsWindow: NSWindow?

    // MARK: - App Lifecycle

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Hide from dock - menu bar only app
        NSApp.setActivationPolicy(.accessory)

        // Setup menu bar
        setupStatusItem()
        setupPopover()
        setupMainMenu()

        // Listen for settings notification
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleOpenSettings),
            name: .openSettings,
            object: nil
        )

        // Listen for quit notification
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleQuitApp),
            name: .quitApp,
            object: nil
        )

        // Listen for logout notification
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleLogout),
            name: .logout,
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

        // Start network monitoring
        NetworkMonitor.shared.startMonitoring()

        // Auto-show popover on first launch (onboarding)
        if appState.phase == .onboarding {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { [weak self] in
                self?.showPopover()
            }
        }
    }

    private func showPopover() {
        guard let button = statusItem.button else { return }
        popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
    }

    @objc private func handleQuitApp() {
        // Close any open windows first
        settingsWindow?.close()
        popover.performClose(nil)

        // Then quit
        quitApp()
    }

    @objc private func handleLogout() {
        // Close settings window
        settingsWindow?.close()

        // Reset to onboarding
        appState.resetOnboarding()
    }

    @objc private func handleNetworkChange() {
        print("[OximyApp] Network changed - checking if proxy needs reconfiguration")

        Task {
            // Only reconfigure if we're connected and proxy was enabled
            guard appState.phase == .connected,
                  ProxyService.shared.isProxyEnabled,
                  let port = MITMService.shared.currentPort else {
                print("[OximyApp] Skipping proxy reconfiguration (not in connected state or proxy not enabled)")
                return
            }

            do {
                // Re-enable proxy on all current network services
                try await ProxyService.shared.enableProxy(port: port)
                print("[OximyApp] Proxy reconfigured successfully for new network")
            } catch {
                print("[OximyApp] Failed to reconfigure proxy: \(error)")
                appState.connectionStatus = .error("Network change failed")
            }
        }
    }

    @objc private func handleMitmproxyFailed() {
        print("[OximyApp] mitmproxy failed permanently")
        appState.connectionStatus = .error("Proxy service failed")
    }

    private func setupMainMenu() {
        let mainMenu = NSMenu()

        // App menu (Oximy)
        let appMenu = NSMenu()
        appMenu.addItem(NSMenuItem(title: "About Oximy", action: #selector(showAbout), keyEquivalent: ""))
        appMenu.addItem(NSMenuItem.separator())
        // NO keyboard shortcut - quit only via explicit button
        appMenu.addItem(NSMenuItem(title: "Quit Oximy", action: #selector(quitApp), keyEquivalent: ""))

        let appMenuItem = NSMenuItem()
        appMenuItem.submenu = appMenu
        mainMenu.addItem(appMenuItem)

        NSApp.mainMenu = mainMenu
    }

    @objc private func showAbout() {
        NSApp.orderFrontStandardAboutPanel(nil)
    }

    private var allowQuit = false

    @objc private func quitApp() {
        print("[OximyApp] Quit requested - setting allowQuit=true")
        allowQuit = true

        // Small delay to ensure UI cleanup completes
        DispatchQueue.main.async {
            NSApp.terminate(nil)
        }
    }

    // Block CMD+Q unless explicitly allowed via quitApp()
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        print("[OximyApp] applicationShouldTerminate called, allowQuit=\(allowQuit)")
        if allowQuit {
            print("[OximyApp] Allowing termination")
            return .terminateNow
        }
        // CMD+Q pressed - close popover and/or settings window, but don't quit
        if popover.isShown {
            popover.performClose(nil)
        }
        if let window = settingsWindow, window.isVisible {
            window.close()
        }
        return .terminateCancel
    }

    @objc private func handleOpenSettings() {
        openSettings()
    }

    func applicationWillTerminate(_ notification: Notification) {
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

        menu.addItem(NSMenuItem(title: "Settings...", action: #selector(openSettingsFromMenu), keyEquivalent: ","))
        menu.addItem(NSMenuItem(title: "Send Feedback", action: #selector(sendFeedback), keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit Oximy", action: #selector(quitApp), keyEquivalent: ""))

        statusItem.menu = menu
        statusItem.button?.performClick(nil)
        statusItem.menu = nil  // Remove menu so left-click works normally again
    }

    @objc private func openSettingsFromMenu() {
        openSettings()
    }

    @objc private func sendFeedback() {
        NSWorkspace.shared.open(Constants.supportURL)
    }

    private var clickMonitor: Any?

    private func setupPopover() {
        popover = NSPopover()
        popover.contentSize = NSSize(width: 320, height: 400)
        // Use .applicationDefined so clicking buttons inside doesn't close the popover
        popover.behavior = .applicationDefined
        popover.animates = true

        // Set the main content view
        let contentView = MainContentView()
            .environmentObject(appState)

        popover.contentViewController = NSHostingController(rootView: contentView)

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

            // Ensure the popover window becomes key
            popover.contentViewController?.view.window?.makeKey()
        }
    }

    func closePopover() {
        popover.performClose(nil)
    }

    func openSettings() {
        // Close the popover first
        popover.performClose(nil)

        // If window already exists, just bring it to front
        if let window = settingsWindow, window.isVisible {
            window.makeKeyAndOrderFront(nil)
            // Show in dock & CMD+Tab when settings is open
            NSApp.setActivationPolicy(.regular)
            NSApp.activate(ignoringOtherApps: true)
            return
        }

        // Create settings window
        let settingsView = SettingsView()
            .environmentObject(appState)

        let hostingController = NSHostingController(rootView: settingsView)

        let window = NSWindow(contentViewController: hostingController)
        window.title = "Oximy Settings"
        window.styleMask = [.titled, .closable, .miniaturizable]
        window.center()
        window.setFrameAutosaveName("SettingsWindow")
        window.isReleasedWhenClosed = false
        window.delegate = self

        self.settingsWindow = window

        // Show in dock & CMD+Tab when settings is open
        NSApp.setActivationPolicy(.regular)
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
}

// MARK: - NSWindowDelegate
extension AppDelegate: NSWindowDelegate {
    func windowWillClose(_ notification: Notification) {
        guard let window = notification.object as? NSWindow,
              window == settingsWindow else { return }

        // Hide from dock when settings closes (back to menu bar only)
        NSApp.setActivationPolicy(.accessory)
    }

    // Prevent CMD+Q from quitting - just close the window
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return false
    }
}

// MARK: - Main Content View (Router)

struct MainContentView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        Group {
            switch appState.phase {
            case .onboarding:
                OnboardingView()
            case .permissions:
                PermissionsView()
            case .login:
                LoginView()
            case .connected:
                StatusView()
            }
        }
        .frame(width: 320, height: 400)
    }
}
