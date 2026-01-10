import SwiftUI

struct PermissionsView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var certService = CertificateService.shared
    @StateObject private var proxyService = ProxyService.shared
    @StateObject private var mitmService = MITMService.shared

    @State private var isInstallingCert = false
    @State private var isEnablingProxy = false
    @State private var errorMessage: String?

    var body: some View {
        VStack(spacing: 0) {
            // Header
            VStack(spacing: 8) {
                Image(systemName: "shield.checkered")
                    .font(.system(size: 40))
                    .foregroundColor(.accentColor)

                Text("System Access Required")
                    .font(.title2)
                    .fontWeight(.semibold)

                Text("Oximy needs these permissions to monitor AI traffic")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding(.top, 32)
            .padding(.horizontal, 24)

            Spacer()

            // Permission Items
            VStack(spacing: 16) {
                PermissionRow(
                    title: "Security Certificate",
                    description: "Required to inspect HTTPS traffic",
                    isGranted: certService.isCAInstalled,
                    isLoading: isInstallingCert,
                    action: installCertificate
                )

                PermissionRow(
                    title: "Network Proxy",
                    description: "Route traffic through Oximy",
                    isGranted: proxyService.isProxyEnabled,
                    isLoading: isEnablingProxy,
                    action: enableProxy
                )
            }
            .padding(.horizontal, 24)

            // Error message
            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
                    .padding(.horizontal, 24)
                    .padding(.top, 12)
                    .multilineTextAlignment(.center)
            }

            Spacer()

            // Continue Button
            Button(action: {
                appState.completePermissions()
            }) {
                Text("Continue")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(!certService.isCAInstalled || !proxyService.isProxyEnabled)
            .padding(.horizontal, 24)
            .padding(.bottom, 24)
        }
        .background(Color(nsColor: .windowBackgroundColor))
        .onAppear {
            // Check current status
            certService.checkStatus()
            proxyService.checkStatus()
        }
    }

    // MARK: - Actions

    private func installCertificate() {
        isInstallingCert = true
        errorMessage = nil

        Task {
            do {
                // Generate CA if needed
                try await certService.generateCA()

                // Install to Keychain (will prompt for password)
                try await certService.installCA()

                // Update app state
                appState.isCertificateInstalled = true

            } catch {
                errorMessage = error.localizedDescription
            }

            isInstallingCert = false
        }
    }

    private func enableProxy() {
        isEnablingProxy = true
        errorMessage = nil

        Task {
            do {
                // Start mitmproxy first
                try await mitmService.start()

                guard let port = mitmService.currentPort else {
                    throw ProxyError.commandFailed("mitmproxy failed to start")
                }

                // Enable system proxy
                try await proxyService.enableProxy(port: port)

                // Update app state
                appState.isProxyEnabled = true

            } catch {
                errorMessage = error.localizedDescription
                // Stop mitmproxy if proxy setup failed
                mitmService.stop()
            }

            isEnablingProxy = false
        }
    }
}

struct PermissionRow: View {
    let title: String
    let description: String
    let isGranted: Bool
    var isLoading: Bool = false
    let action: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // Status Icon
            if isLoading {
                ProgressView()
                    .scaleEffect(0.8)
                    .frame(width: 24, height: 24)
            } else {
                Image(systemName: isGranted ? "checkmark.circle.fill" : "circle")
                    .font(.title2)
                    .foregroundColor(isGranted ? .green : .gray)
            }

            // Text
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.headline)

                Text(description)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            // Action Button
            if !isGranted {
                Button("Grant") {
                    action()
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .disabled(isLoading)
            }
        }
        .padding(12)
        .background(Color(nsColor: .controlBackgroundColor))
        .cornerRadius(8)
    }
}

#Preview {
    PermissionsView()
        .environmentObject(AppState())
        .frame(width: 320, height: 400)
}
