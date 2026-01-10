import SwiftUI

struct StatusView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(spacing: 0) {
            // Settings Button (top right)
            HStack {
                Spacer()
                Button(action: openSettings) {
                    Image(systemName: "gearshape")
                        .font(.title3)
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
                .padding(16)
            }

            Spacer()

            // Connection Status
            VStack(spacing: 16) {
                // Status Indicator
                HStack(spacing: 8) {
                    Circle()
                        .fill(appState.connectionStatus.color)
                        .frame(width: 12, height: 12)

                    Text(appState.connectionStatus.label)
                        .font(.headline)
                }

                // Divider
                Divider()
                    .padding(.horizontal, 40)

                // Device & Workspace Info
                VStack(spacing: 8) {
                    InfoRow(label: "Device", value: appState.deviceName)
                    InfoRow(label: "Workspace", value: appState.workspaceName)
                }

                // Divider
                Divider()
                    .padding(.horizontal, 40)

                // Health Status
                VStack(spacing: 4) {
                    HStack(spacing: 4) {
                        Image(systemName: "heart.fill")
                            .foregroundColor(.green)
                        Text("Healthy")
                            .font(.subheadline)
                    }

                    Text("Port \(appState.currentPort)")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    if appState.eventsCapturedToday > 0 {
                        Text("\(appState.eventsCapturedToday) events captured today")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }

            Spacer()

            // Version
            Text("v1.0.0")
                .font(.caption2)
                .foregroundColor(.secondary)
                .padding(.bottom, 16)
        }
        .background(Color(nsColor: .windowBackgroundColor))
        .onAppear {
            // TODO: Start monitoring and update status
            appState.connectionStatus = .connected
        }
    }

    private func openSettings() {
        NotificationCenter.default.post(name: .openSettings, object: nil)
    }
}

struct InfoRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack {
            Text(label)
                .font(.subheadline)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .font(.subheadline)
                .fontWeight(.medium)
        }
        .padding(.horizontal, 32)
    }
}

#Preview {
    StatusView()
        .environmentObject({
            let state = AppState()
            state.workspaceName = "Oximy Team"
            state.connectionStatus = .connected
            state.eventsCapturedToday = 127
            return state
        }())
        .frame(width: 320, height: 400)
}
