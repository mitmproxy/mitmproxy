import SwiftUI

struct HomeTab: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var proxyService = ProxyService.shared
    @StateObject private var mitmService = MITMService.shared
    @StateObject private var certService = CertificateService.shared
    @StateObject private var syncService = SyncService.shared

    @State private var isToggling = false

    var body: some View {
        VStack(spacing: 20) {
            Spacer()

            // Connection Status Card
            VStack(spacing: 16) {
                // Status Icon
                ZStack {
                    Circle()
                        .fill(statusColor.opacity(0.15))
                        .frame(width: 80, height: 80)

                    if isToggling {
                        ProgressView()
                            .scaleEffect(1.2)
                    } else {
                        Image(systemName: statusIcon)
                            .font(.system(size: 36))
                            .foregroundColor(statusColor)
                    }
                }

                // Status Text
                Text(statusText)
                    .font(.title3)
                    .fontWeight(.semibold)

                if proxyService.isProxyEnabled, let port = proxyService.configuredPort {
                    Text("Port \(port)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            // Toggle Button
            Button(action: toggleProxy) {
                HStack {
                    Image(systemName: proxyService.isProxyEnabled ? "stop.fill" : "play.fill")
                    Text(proxyService.isProxyEnabled ? "Stop Monitoring" : "Start Monitoring")
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 4)
            }
            .buttonStyle(.borderedProminent)
            .tint(proxyService.isProxyEnabled ? .orange : .accentColor)
            .disabled(isToggling || !certService.isCAInstalled)
            .padding(.horizontal, 32)

            if !certService.isCAInstalled {
                Text("Install certificate in Settings first")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            // Device Info & Sync Status
            VStack(spacing: 8) {
                InfoRow(label: "Device", value: appState.deviceName)

                if appState.isLoggedIn && !appState.workspaceName.isEmpty {
                    InfoRow(label: "Organization", value: appState.workspaceName)
                }

                Divider()
                    .padding(.vertical, 4)

                // Sync Status
                HStack {
                    Text("Events Pending")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                    if syncService.isSyncing {
                        HStack(spacing: 4) {
                            ProgressView()
                                .scaleEffect(0.5)
                            Text("Syncing...")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    } else {
                        Text("\(syncService.pendingEventCount)")
                            .font(.caption)
                            .fontWeight(.medium)
                    }
                }

                if let lastSync = syncService.lastSyncTime {
                    InfoRow(label: "Last Sync", value: lastSync.relativeFormatted)
                }

                if let error = syncService.syncError {
                    HStack {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.orange)
                            .font(.caption)
                        Text(error)
                            .font(.caption2)
                            .foregroundColor(.orange)
                            .lineLimit(1)
                    }
                }
            }
            .padding()
            .background(Color(nsColor: .controlBackgroundColor))
            .cornerRadius(10)
            .padding(.horizontal, 16)
            .padding(.bottom, 8)
        }
        .onAppear {
            certService.checkStatus()
            proxyService.checkStatus()
        }
    }

    private var statusColor: Color {
        if proxyService.isProxyEnabled {
            return .green
        } else if !certService.isCAInstalled {
            return .gray
        } else {
            return .orange
        }
    }

    private var statusIcon: String {
        if proxyService.isProxyEnabled {
            return "checkmark.shield.fill"
        } else if !certService.isCAInstalled {
            return "shield.slash"
        } else {
            return "shield"
        }
    }

    private var statusText: String {
        if proxyService.isProxyEnabled {
            return "Monitoring Active"
        } else if !certService.isCAInstalled {
            return "Setup Required"
        } else {
            return "Monitoring Paused"
        }
    }

    private func toggleProxy() {
        isToggling = true

        Task {
            do {
                if proxyService.isProxyEnabled {
                    // Stop
                    try await proxyService.disableProxy()
                    mitmService.stop()
                    appState.isProxyEnabled = false
                } else {
                    // Start
                    try await mitmService.start()
                    guard let port = mitmService.currentPort else {
                        throw ProxyError.commandFailed("Failed to start proxy")
                    }
                    try await proxyService.enableProxy(port: port)
                    appState.isProxyEnabled = true
                    appState.currentPort = port
                }
            } catch {
                print("Toggle proxy error: \(error)")
                mitmService.stop()
            }
            isToggling = false
        }
    }
}

struct InfoRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .font(.caption)
                .fontWeight(.medium)
        }
    }
}

#Preview {
    HomeTab()
        .environmentObject(AppState())
        .frame(width: 340, height: 350)
}
