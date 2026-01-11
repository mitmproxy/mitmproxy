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
            certService.checkStatus()
            proxyService.checkStatus()
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
