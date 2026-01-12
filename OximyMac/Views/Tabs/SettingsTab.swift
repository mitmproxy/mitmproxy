import SwiftUI

struct SettingsTab: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var certService = CertificateService.shared
    @StateObject private var proxyService = ProxyService.shared
    @StateObject private var mitmService = MITMService.shared
    @StateObject private var updateService = UpdateService.shared
    @StateObject private var syncService = SyncService.shared

    @State private var isProcessingCert = false
    @State private var isCheckingForUpdates = false
    @State private var showClearDataConfirmation = false
    @State private var isClearingData = false
    @State private var isRefreshingBundle = false
    @State private var lastBundleRefresh: Date? = nil
    @State private var isForceSyncing = false

    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                // Updates Section
                SettingsSection(title: "Updates", icon: "arrow.down.circle.fill") {
                    VStack(spacing: 12) {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("App Updates")
                                    .font(.subheadline)
                                    .fontWeight(.medium)

                                if updateService.updateAvailable, let version = updateService.latestVersion {
                                    Text("Version \(version) available")
                                        .font(.caption)
                                        .foregroundColor(.orange)
                                } else {
                                    Text("Version \(updateService.currentVersion)")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }

                            Spacer()

                            Button {
                                updateService.checkForUpdates()
                            } label: {
                                if isCheckingForUpdates {
                                    ProgressView()
                                        .scaleEffect(0.7)
                                } else {
                                    Text("Check for Updates")
                                }
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.small)
                            .disabled(!updateService.canCheckForUpdates || isCheckingForUpdates)
                        }

                        Divider()

                        Toggle("Automatic Updates", isOn: Binding(
                            get: { updateService.automaticallyChecksForUpdates },
                            set: { updateService.automaticallyChecksForUpdates = $0 }
                        ))
                        .toggleStyle(.switch)
                        .font(.caption)
                    }
                }

                // Bundle Section
                SettingsSection(title: "Detection Bundle", icon: "doc.text.fill") {
                    VStack(spacing: 12) {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("OISP Bundle")
                                    .font(.subheadline)
                                    .fontWeight(.medium)

                                if let lastRefresh = lastBundleRefresh {
                                    Text("Last updated: \(lastRefresh, formatter: Self.timeFormatter)")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                } else {
                                    Text("Auto-refreshes every 30 minutes")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }

                            Spacer()

                            Button {
                                refreshBundle()
                            } label: {
                                if isRefreshingBundle {
                                    ProgressView()
                                        .scaleEffect(0.7)
                                } else {
                                    Text("Refresh Now")
                                }
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.small)
                            .disabled(isRefreshingBundle || !mitmService.isRunning)
                        }

                        if !mitmService.isRunning {
                            Text("Start proxy to enable bundle refresh")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                        }
                    }
                }

                // Certificate Section
                SettingsSection(title: "Certificate", icon: "lock.shield.fill") {
                    VStack(spacing: 12) {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("Oximy CA")
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                                Text(certService.isCAInstalled ? "Installed & Trusted" : "Not installed")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }

                            Spacer()

                            if isProcessingCert {
                                ProgressView()
                                    .scaleEffect(0.8)
                            } else {
                                Toggle("", isOn: Binding(
                                    get: { certService.isCAInstalled },
                                    set: { _ in toggleCertificate() }
                                ))
                                .toggleStyle(.switch)
                                .labelsHidden()
                            }
                        }

                        if certService.isCAInstalled {
                            Divider()

                            HStack(spacing: 12) {
                                Button("Show in Finder") {
                                    NSWorkspace.shared.selectFile(
                                        Constants.caCertPath.path,
                                        inFileViewerRootedAtPath: Constants.oximyDir.path
                                    )
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)

                                Button("Open Keychain") {
                                    if let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.apple.keychainaccess") {
                                        NSWorkspace.shared.open(url)
                                    }
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)
                            }
                        }
                    }
                }

                // Account Section
                SettingsSection(title: "Account", icon: "person.circle.fill") {
                    if appState.isLoggedIn {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(appState.workspaceName.isEmpty ? "Connected" : appState.workspaceName)
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                                Text("Logged in")
                                    .font(.caption)
                                    .foregroundColor(.green)
                            }

                            Spacer()

                            Button("Log Out") {
                                appState.logout()
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.small)
                        }
                    } else {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("Not connected")
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                                Text("Link to your workspace")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }

                            Spacer()

                            Button("Connect") {
                                NSWorkspace.shared.open(Constants.signUpURL)
                            }
                            .buttonStyle(.borderedProminent)
                            .controlSize(.small)
                        }
                    }
                }

                // Local Data Section
                SettingsSection(title: "Local Data", icon: "externaldrive.fill") {
                    VStack(alignment: .leading, spacing: 10) {
                        // Storage info
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("Local Storage")
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                                Text("\(syncService.traceFileCount) files • \(syncService.localStorageSizeFormatted)")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            Spacer()
                        }

                        if syncService.pendingEventCount > 0 {
                            HStack {
                                Image(systemName: "clock.arrow.circlepath")
                                    .foregroundColor(.orange)
                                    .font(.caption)
                                Text("\(syncService.pendingEventCount) events pending sync")
                                    .font(.caption)
                                    .foregroundColor(.orange)

                                Spacer()

                                Button {
                                    forceSync()
                                } label: {
                                    if isForceSyncing {
                                        ProgressView()
                                            .scaleEffect(0.6)
                                    } else {
                                        Text("Sync Now")
                                    }
                                }
                                .buttonStyle(.borderedProminent)
                                .controlSize(.small)
                                .disabled(isForceSyncing || !appState.isLoggedIn)
                            }
                        }

                        Divider()

                        HStack(spacing: 12) {
                            Button {
                                syncService.openTracesFolder()
                            } label: {
                                Label("Open Folder", systemImage: "folder")
                                    .font(.caption)
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.small)

                            Button(role: .destructive) {
                                showClearDataConfirmation = true
                            } label: {
                                if isClearingData {
                                    ProgressView()
                                        .scaleEffect(0.6)
                                } else {
                                    Label("Clear Data", systemImage: "trash")
                                        .font(.caption)
                                }
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.small)
                            .disabled(isClearingData || syncService.traceFileCount == 0)
                        }

                        Text("Clearing data removes all locally stored events. Synced events are not affected.")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
                .confirmationDialog(
                    "Clear Local Data?",
                    isPresented: $showClearDataConfirmation,
                    titleVisibility: .visible
                ) {
                    Button("Clear All Local Events", role: .destructive) {
                        clearLocalData()
                    }
                    Button("Cancel", role: .cancel) {}
                } message: {
                    Text("This will delete \(syncService.pendingEventCount) pending events and \(syncService.traceFileCount) trace files. This cannot be undone.")
                }

                // Advanced Section
                SettingsSection(title: "Advanced", icon: "wrench.and.screwdriver.fill") {
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("Port")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Spacer()
                            Text("\(proxyService.configuredPort ?? Constants.preferredPort)")
                                .font(.caption)
                                .fontWeight(.medium)
                        }

                        HStack {
                            Text("Config Directory")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Spacer()
                            Text("~/.oximy")
                                .font(.caption)
                                .fontWeight(.medium)
                        }

                        Divider()

                        Button(role: .destructive) {
                            appState.reset()
                        } label: {
                            Text("Reset All Settings")
                                .font(.caption)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                    }
                }
            }
            .padding(16)
        }
        .onAppear {
            // Only check cert status on appear - it rarely changes
            // DO NOT call proxyService.checkStatus() here - it overwrites the known state
            // and can cause flickering when moving screens
            certService.checkStatus()
        }
    }

    private func toggleCertificate() {
        isProcessingCert = true

        Task {
            do {
                if certService.isCAInstalled {
                    // Turn off proxy first
                    if proxyService.isProxyEnabled {
                        try await proxyService.disableProxy()
                        mitmService.stop()
                        appState.isProxyEnabled = false
                    }
                    try await certService.removeCA()
                    appState.isCertificateInstalled = false
                } else {
                    try await certService.generateCA()
                    try await certService.installCA()
                    appState.isCertificateInstalled = true
                }
            } catch {
                print("Certificate error: \(error)")
            }
            isProcessingCert = false
        }
    }

    private func clearLocalData() {
        isClearingData = true

        Task {
            do {
                try syncService.clearLocalData()
            } catch {
                print("Failed to clear local data: \(error)")
            }
            isClearingData = false
        }
    }

    private func forceSync() {
        isForceSyncing = true

        Task {
            await syncService.syncNow()
            isForceSyncing = false
        }
    }

    private func refreshBundle() {
        isRefreshingBundle = true

        Task {
            do {
                // Force bundle refresh by restarting mitmproxy
                try await mitmService.refreshBundle()

                // Re-enable proxy on the new port (port may change after restart)
                if let newPort = mitmService.currentPort {
                    try await proxyService.enableProxy(port: newPort)
                }

                lastBundleRefresh = Date()
            } catch {
                print("Failed to refresh bundle: \(error)")
            }
            isRefreshingBundle = false
        }
    }

    // Time formatter for last bundle refresh
    private static let timeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .none
        formatter.timeStyle = .short
        return formatter
    }()
}

struct SettingsSection<Content: View>: View {
    let title: String
    let icon: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text(title.uppercased())
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundColor(.secondary)
            }

            content
                .padding(12)
                .background(Color(nsColor: .controlBackgroundColor))
                .cornerRadius(8)
        }
    }
}

#Preview {
    SettingsTab()
        .environmentObject(AppState())
        .frame(width: 340, height: 400)
}
