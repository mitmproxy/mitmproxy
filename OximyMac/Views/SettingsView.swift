import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @State private var showPurgeConfirmation = false
    @State private var showLogoutConfirmation = false
    @State private var actionFeedback: String?
    @State private var showingFeedback = false

    // Quit confirmation state
    @State private var quitTapCount = 0
    @State private var quitResetTask: Task<Void, Never>?

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            Text("Settings")
                .font(.title2)
                .fontWeight(.semibold)
                .padding(.horizontal, 20)
                .padding(.top, 20)
                .padding(.bottom, 16)

            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    // About Section
                    SettingsSection(title: "ABOUT") {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Oximy")
                                .font(.headline)
                            Text("Version 1.0.0 (Build 1)")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }

                    // Support Section
                    SettingsSection(title: "SUPPORT") {
                        VStack(spacing: 12) {
                            SettingsButton(title: "Help & Documentation", icon: "questionmark.circle") {
                                NSWorkspace.shared.open(Constants.helpURL)
                            }

                            SettingsButton(title: "Report an Issue", icon: "exclamationmark.bubble") {
                                NSWorkspace.shared.open(Constants.supportURL)
                            }
                        }
                    }

                    // Legal Section
                    SettingsSection(title: "LEGAL") {
                        VStack(spacing: 12) {
                            SettingsButton(title: "Terms of Service", icon: "doc.text") {
                                NSWorkspace.shared.open(Constants.termsURL)
                            }

                            SettingsButton(title: "Privacy Policy", icon: "hand.raised") {
                                NSWorkspace.shared.open(Constants.privacyURL)
                            }

                            SettingsButton(title: "Open Source (GitHub)", icon: "chevron.left.forwardslash.chevron.right") {
                                NSWorkspace.shared.open(Constants.githubURL)
                            }
                        }
                    }

                    // Advanced Section
                    SettingsSection(title: "ADVANCED") {
                        VStack(spacing: 12) {
                            // Log Location
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Log file location")
                                    .font(.subheadline)
                                Text(Constants.tracesDir.path)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                    .lineLimit(1)
                                    .truncationMode(.middle)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.vertical, 4)

                            Divider()

                            SettingsButton(title: "Refresh Spec Config", icon: "arrow.clockwise") {
                                showFeedback("Spec config refreshed")
                            }

                            SettingsButton(title: "Purge Cache & Logs", icon: "trash", isDestructive: true) {
                                showPurgeConfirmation = true
                            }

                            SettingsButton(title: "Force Sync to Cloud", icon: "arrow.triangle.2.circlepath") {
                                showFeedback("Sync initiated")
                            }
                        }
                    }

                    // Account Section
                    SettingsSection(title: "ACCOUNT") {
                        VStack(spacing: 12) {
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Workspace")
                                        .font(.subheadline)
                                    Text(appState.workspaceName)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                                Spacer()
                            }

                            SettingsButton(title: "Log Out", icon: "rectangle.portrait.and.arrow.right", isDestructive: true) {
                                showLogoutConfirmation = true
                            }

                            Divider()

                            // Quit button with double-tap confirmation
                            Button(action: handleQuitTap) {
                                HStack {
                                    Image(systemName: "power")
                                        .frame(width: 20)
                                    Text(quitButtonText)
                                    Spacer()
                                    if quitTapCount == 1 {
                                        Text("Tap again")
                                            .font(.caption)
                                            .foregroundColor(.orange)
                                    }
                                }
                                .foregroundColor(.red)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 20)
            }
        }
        .frame(width: 350, height: 500)
        .background(Color(nsColor: .windowBackgroundColor))
        .alert("Purge Cache & Logs?", isPresented: $showPurgeConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Purge", role: .destructive) {
                purgeCache()
            }
        } message: {
            Text("This will delete all cached data and log files. This action cannot be undone.")
        }
        .alert("Log Out?", isPresented: $showLogoutConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Log Out", role: .destructive) {
                // Post logout notification - AppDelegate will close settings and reset state
                NotificationCenter.default.post(name: .logout, object: nil)
            }
        } message: {
            Text("You will need to enter your 6-digit code again to reconnect.")
        }
        .overlay(alignment: .bottom) {
            if showingFeedback, let feedback = actionFeedback {
                Text(feedback)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(.white)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(Color.green.cornerRadius(8))
                    .padding(.bottom, 20)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .animation(.easeInOut(duration: 0.3), value: showingFeedback)
    }

    private func showFeedback(_ message: String) {
        actionFeedback = message
        showingFeedback = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            showingFeedback = false
        }
    }

    // MARK: - Quit Double-Tap

    private var quitButtonText: String {
        quitTapCount == 1 ? "Confirm Quit" : "Quit Oximy"
    }

    private func handleQuitTap() {
        quitTapCount += 1

        if quitTapCount >= 2 {
            // Double-tap confirmed - quit the app
            NotificationCenter.default.post(name: .quitApp, object: nil)
        } else {
            // First tap - show confirmation and reset after 3 seconds
            quitResetTask?.cancel()
            quitResetTask = Task {
                try? await Task.sleep(nanoseconds: 3_000_000_000) // 3 seconds
                if !Task.isCancelled {
                    await MainActor.run {
                        quitTapCount = 0
                    }
                }
            }
        }
    }

    private func purgeCache() {
        let fileManager = FileManager.default

        do {
            // Remove traces
            let tracesDir = Constants.tracesDir
            if fileManager.fileExists(atPath: tracesDir.path) {
                try fileManager.removeItem(at: tracesDir)
            }

            // Remove logs
            let logsDir = Constants.logsDir
            if fileManager.fileExists(atPath: logsDir.path) {
                try fileManager.removeItem(at: logsDir)
            }

            // Remove bundle cache
            let bundleCache = Constants.bundleCachePath
            if fileManager.fileExists(atPath: bundleCache.path) {
                try fileManager.removeItem(at: bundleCache)
            }

            // Recreate directories
            try fileManager.createDirectory(at: tracesDir, withIntermediateDirectories: true)
            try fileManager.createDirectory(at: logsDir, withIntermediateDirectories: true)

            showFeedback("Cache & logs purged")
        } catch {
            showFeedback("Error: \(error.localizedDescription)")
        }
    }
}

struct SettingsSection<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(.secondary)

            VStack(alignment: .leading, spacing: 0) {
                content
            }
            .padding(12)
            .background(Color(nsColor: .controlBackgroundColor))
            .cornerRadius(8)
        }
    }
}

struct SettingsButton: View {
    let title: String
    let icon: String
    var isDestructive: Bool = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Image(systemName: icon)
                    .frame(width: 20)
                Text(title)
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .foregroundColor(isDestructive ? .red : .primary)
        }
        .buttonStyle(.plain)
    }
}

#Preview {
    SettingsView()
        .environmentObject({
            let state = AppState()
            state.workspaceName = "Oximy Team"
            return state
        }())
}
