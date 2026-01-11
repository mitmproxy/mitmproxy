import SwiftUI

/// Main view - shows Setup or Dashboard based on state
struct MainView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        Group {
            switch appState.phase {
            case .setup:
                SetupView()
            case .ready:
                DashboardView()
            }
        }
        .frame(width: 340, height: 420)
    }
}

// MARK: - Setup View (First Run)

struct SetupView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var certService = CertificateService.shared
    @StateObject private var proxyService = ProxyService.shared
    @StateObject private var mitmService = MITMService.shared

    @State private var isProcessingCert = false
    @State private var isProcessingProxy = false
    @State private var errorMessage: String?

    var body: some View {
        VStack(spacing: 0) {
            // Header
            VStack(spacing: 12) {
                Image("Oximy")
                    .resizable()
                    .frame(width: 60, height: 60)
                    .cornerRadius(12)

                Text("Welcome to Oximy")
                    .font(.title2)
                    .fontWeight(.semibold)

                Text("Enable these permissions to start monitoring AI traffic")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            }
            .padding(.top, 24)

            Spacer()

            // Setup Steps
            VStack(spacing: 16) {
                SetupStep(
                    number: 1,
                    title: "Install Certificate",
                    description: "Adds Oximy CA to your Keychain",
                    isComplete: certService.isCAInstalled,
                    isProcessing: isProcessingCert
                ) {
                    installCertificate()
                }

                SetupStep(
                    number: 2,
                    title: "Enable Proxy",
                    description: "Routes traffic through Oximy",
                    isComplete: proxyService.isProxyEnabled,
                    isProcessing: isProcessingProxy,
                    isDisabled: !certService.isCAInstalled
                ) {
                    enableProxy()
                }
            }
            .padding(.horizontal, 24)

            // Error
            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
                    .padding(.top, 12)
                    .padding(.horizontal)
                    .lineLimit(2)
            }

            Spacer()

            // Start Button
            Button(action: startMonitoring) {
                HStack {
                    if allComplete {
                        Image(systemName: "play.fill")
                    }
                    Text(allComplete ? "Start Monitoring" : "Complete Setup Above")
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(!allComplete)
            .padding(.horizontal, 24)
            .padding(.bottom, 24)
        }
        .background(Color(nsColor: .windowBackgroundColor))
        .onAppear {
            certService.checkStatus()
            proxyService.checkStatus()
        }
    }

    private var allComplete: Bool {
        certService.isCAInstalled && proxyService.isProxyEnabled
    }

    private func installCertificate() {
        isProcessingCert = true
        errorMessage = nil

        Task {
            do {
                try await certService.generateCA()
                try await certService.installCA()
                appState.isCertificateInstalled = true
            } catch {
                errorMessage = error.localizedDescription
            }
            isProcessingCert = false
        }
    }

    private func enableProxy() {
        guard certService.isCAInstalled else {
            errorMessage = "Install certificate first"
            return
        }

        isProcessingProxy = true
        errorMessage = nil

        Task {
            do {
                try await mitmService.start()
                guard let port = mitmService.currentPort else {
                    throw ProxyError.commandFailed("Proxy failed to start")
                }
                try await proxyService.enableProxy(port: port)
                appState.isProxyEnabled = true
                appState.currentPort = port
            } catch {
                errorMessage = error.localizedDescription
                mitmService.stop()
            }
            isProcessingProxy = false
        }
    }

    private func startMonitoring() {
        appState.completeSetup()
    }
}

// MARK: - Setup Step Component

struct SetupStep: View {
    let number: Int
    let title: String
    let description: String
    let isComplete: Bool
    var isProcessing: Bool = false
    var isDisabled: Bool = false
    let action: () -> Void

    var body: some View {
        Button(action: {
            if !isDisabled && !isProcessing && !isComplete {
                action()
            }
        }) {
            HStack(spacing: 16) {
                // Number/Check
                ZStack {
                    Circle()
                        .fill(circleColor)
                        .frame(width: 36, height: 36)

                    if isProcessing {
                        ProgressView()
                            .scaleEffect(0.6)
                    } else if isComplete {
                        Image(systemName: "checkmark")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(.white)
                    } else {
                        Text("\(number)")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(isDisabled ? .secondary : .white)
                    }
                }

                // Text
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.headline)
                        .foregroundColor(isDisabled ? .secondary : .primary)
                    Text(description)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()

                // Action indicator
                if !isComplete && !isDisabled {
                    Image(systemName: "arrow.right.circle.fill")
                        .foregroundColor(.accentColor)
                }
            }
            .padding(16)
            .background(Color(nsColor: .controlBackgroundColor))
            .cornerRadius(12)
        }
        .buttonStyle(.plain)
        .opacity(isDisabled ? 0.5 : 1.0)
    }

    private var circleColor: Color {
        if isComplete {
            return .green
        } else if isDisabled {
            return .gray.opacity(0.3)
        } else {
            return .accentColor
        }
    }
}

// MARK: - Dashboard View (After Setup)

struct DashboardView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(spacing: 0) {
            // Tab Content
            Group {
                switch appState.selectedTab {
                case .home:
                    HomeTab()
                case .settings:
                    SettingsTab()
                case .support:
                    SupportTab()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            // Tab Bar
            HStack(spacing: 0) {
                ForEach(AppState.MainTab.allCases, id: \.self) { tab in
                    TabBarButton(tab: tab, selected: $appState.selectedTab)
                }
            }
            .padding(.top, 8)
            .padding(.bottom, 6)
            .background(Color(nsColor: .controlBackgroundColor).opacity(0.5))
        }
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

// MARK: - Tab Bar Button

struct TabBarButton: View {
    let tab: AppState.MainTab
    @Binding var selected: AppState.MainTab

    var body: some View {
        Button(action: { selected = tab }) {
            VStack(spacing: 4) {
                Image(systemName: tab.icon)
                    .font(.system(size: 20))
                Text(tab.rawValue)
                    .font(.caption2)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 44)
            .contentShape(Rectangle())
            .foregroundColor(selected == tab ? .accentColor : .secondary)
        }
        .buttonStyle(.plain)
    }
}

#Preview {
    MainView()
        .environmentObject(AppState())
}
