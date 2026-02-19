import SwiftUI

struct HomeTab: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var proxyService = ProxyService.shared
    @StateObject private var certService = CertificateService.shared
    @StateObject private var syncService = SyncService.shared
    @StateObject private var remoteStateService = RemoteStateService.shared
    @StateObject private var violationService = ViolationService.shared

    var body: some View {
        VStack(spacing: 0) {
            // Violation Banner (if recent violations exist)
            if !violationService.violations.isEmpty {
                HStack(spacing: 8) {
                    Image(systemName: "shield.lefthalf.filled.trianglebadge.exclamationmark")
                        .font(.caption)
                        .foregroundColor(.orange)

                    Text("\(violationService.violations.count) policy violation\(violationService.violations.count == 1 ? "" : "s") detected")
                        .font(.caption)
                        .fontWeight(.medium)

                    Spacer()
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(Color.orange.opacity(0.1))
            }

            // Main content area - centered
            VStack(spacing: 20) {
                // Connection Status Card
                VStack(spacing: 16) {
                    // Status Icon
                    ZStack {
                        Circle()
                            .fill(statusColor.opacity(0.15))
                            .frame(width: 80, height: 80)

                        Image(systemName: statusIcon)
                            .font(.system(size: 36))
                            .foregroundColor(statusColor)
                    }

                    // Status Text
                    Text(statusText)
                        .font(.title3)
                        .fontWeight(.semibold)

                    // Subtext explaining admin control when paused
                    if !remoteStateService.sensorEnabled {
                        VStack(spacing: 4) {
                            Text("Monitoring paused by administrator")
                                .font(.caption)
                                .foregroundColor(.secondary)

                            if let itSupport = remoteStateService.itSupport, !itSupport.isEmpty {
                                Text("Contact: \(itSupport)")
                                    .font(.caption)
                                    .foregroundColor(.blue)
                            }
                        }
                    }

                    if remoteStateService.proxyActive, let port = proxyService.configuredPort {
                        Text("Port \(port)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                if !certService.isCAInstalled {
                    Text("Install certificate in Settings first")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .frame(maxHeight: .infinity)

            // Device Info & Sync Status - pinned to bottom
            VStack(spacing: 8) {
                InfoRow(label: "Device", value: appState.deviceName)

                if appState.isLoggedIn && !appState.workspaceName.isEmpty {
                    InfoRow(label: "Organization", value: appState.workspaceName)
                }

                Divider()
                    .padding(.vertical, 4)

                // Sensor State
                HStack {
                    Text("Sensor State")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                    HStack(spacing: 4) {
                        Circle()
                            .fill(remoteStateService.sensorEnabled ? Color.green : Color.gray)
                            .frame(width: 6, height: 6)
                        Text(remoteStateService.sensorEnabled ? "ON" : "OFF")
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(remoteStateService.sensorEnabled ? .green : .secondary)
                    }
                }

                // Sync Status
                HStack {
                    Text("Events Pending")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                    Text("\(syncService.pendingEventCount)")
                        .font(.caption)
                        .fontWeight(.medium)
                }

                InfoRow(label: "Last Sync", value: lastSyncText)
            }
            .padding()
            .background(Color(nsColor: .controlBackgroundColor))
            .cornerRadius(10)
            .padding(.horizontal, 16)
            .padding(.bottom, 8)
        }
        .onAppear {
            // Only check cert status on appear - it rarely changes
            // DO NOT call proxyService.checkStatus() here - it overwrites the known state
            // by querying the system, which can cause flickering when moving screens
            // ProxyService.isProxyEnabled is already tracked and updated by enableProxy/disableProxy
            certService.checkStatus()
        }
    }

    private var statusColor: Color {
        if !remoteStateService.sensorEnabled {
            return .yellow  // Paused by admin
        } else if remoteStateService.proxyActive {
            return .green  // Actively monitoring
        } else if !certService.isCAInstalled {
            return .gray  // Setup required
        } else {
            return .orange  // Starting...
        }
    }

    private var statusIcon: String {
        if !remoteStateService.sensorEnabled {
            return "pause.circle.fill"  // Paused by admin
        } else if remoteStateService.proxyActive {
            return "checkmark.shield.fill"  // Actively monitoring
        } else if !certService.isCAInstalled {
            return "shield.slash"  // Setup required
        } else {
            return "arrow.triangle.2.circlepath"  // Starting...
        }
    }

    private var statusText: String {
        if !remoteStateService.sensorEnabled {
            return "Monitoring Paused"
        } else if remoteStateService.proxyActive {
            return "Monitoring Active"
        } else if !certService.isCAInstalled {
            return "Setup Required"
        } else {
            return "Starting..."
        }
    }

    private var lastSyncText: String {
        if let lastSync = syncService.lastSyncTime {
            return lastSync.relativeFormatted
        } else {
            return "–"
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
