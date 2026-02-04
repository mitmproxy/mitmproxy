import SwiftUI

struct SettingsTab: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var certService = CertificateService.shared
    @StateObject private var proxyService = ProxyService.shared
    @StateObject private var mitmService = MITMService.shared

    @State private var isProcessingCert = false

    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
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

                                if MDMConfigService.shared.isManagedDevice {
                                    Text("Managed by your organization")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                } else {
                                    Text("Logged in")
                                        .font(.caption)
                                        .foregroundColor(.green)
                                }
                            }

                            Spacer()

                            // Logout button - hidden when disableUserLogout is true
                            if appState.canLogout {
                                Button("Sign Out") {
                                    appState.logout()
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)
                            }
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

                        // Show managed device indicator
                        if MDMConfigService.shared.isManagedDevice {
                            HStack {
                                Text("Management")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                Spacer()
                                Text("MDM Managed")
                                    .font(.caption)
                                    .fontWeight(.medium)
                                    .foregroundColor(.blue)
                            }
                        }

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
                    // Stop mitmproxy first (addon will disable proxy on cleanup)
                    if mitmService.isRunning {
                        mitmService.stop()
                    }
                    try await certService.removeCA()
                    // Also delete the certificate files so a fresh cert is generated on re-enable
                    // This prevents issues where macOS remembers the old cert was removed/distrusted
                    try certService.deleteCAFiles()
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
