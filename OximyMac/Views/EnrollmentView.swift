import SwiftUI
import AppKit

struct EnrollmentView: View {
    @EnvironmentObject var appState: AppState

    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        VStack(spacing: 0) {
            // Progress indicator - Step 1 of 2
            HStack(spacing: 8) {
                ProgressDot(step: 1, isComplete: false, isCurrent: true)
                ProgressLine(isComplete: false)
                ProgressDot(step: 2, isComplete: false, isCurrent: false)
            }
            .padding(.top, 20)
            .padding(.horizontal, 60)

            // Header
            VStack(spacing: 6) {
                OximyLogo(size: 52)
                    .cornerRadius(12)
                    .padding(.top, 20)

                Text("STEP 1")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundColor(.accentColor)
                    .tracking(1.5)

                Text("Connect Your Workspace")
                    .font(.system(size: 18, weight: .bold))
            }

            // Instructions
            HStack(spacing: 10) {
                Image(systemName: "globe")
                    .font(.system(size: 20))
                    .foregroundColor(.accentColor)

                VStack(alignment: .leading, spacing: 1) {
                    Text("Sign in with your browser")
                        .font(.system(size: 13, weight: .medium))
                    Text("You'll be redirected to authenticate")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                }
                Spacer()
            }
            .padding(12)
            .background(Color.accentColor.opacity(0.1))
            .cornerRadius(10)
            .padding(.horizontal, 24)
            .padding(.top, 16)

            // How it works
            VStack(alignment: .leading, spacing: 12) {
                Text("How it works:")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.secondary)

                HStack(alignment: .top, spacing: 10) {
                    Text("1")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.white)
                        .frame(width: 18, height: 18)
                        .background(Color.accentColor)
                        .clipShape(Circle())

                    Text("Click the button below to open your browser")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }

                HStack(alignment: .top, spacing: 10) {
                    Text("2")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.white)
                        .frame(width: 18, height: 18)
                        .background(Color.accentColor)
                        .clipShape(Circle())

                    Text("Enter your 6-digit code on the web page")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }

                HStack(alignment: .top, spacing: 10) {
                    Text("3")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.white)
                        .frame(width: 18, height: 18)
                        .background(Color.accentColor)
                        .clipShape(Circle())

                    Text("You'll be automatically signed in here")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(nsColor: .controlBackgroundColor))
            .cornerRadius(10)
            .padding(.horizontal, 24)
            .padding(.top, 16)

            // Error message - fixed height container to prevent layout shifts
            VStack {
                if let error = errorMessage {
                    HStack(spacing: 6) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .font(.system(size: 11))
                        Text(error)
                            .font(.system(size: 12))
                    }
                    .foregroundColor(.red)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 8)
                    .background(Color.red.opacity(0.1))
                    .cornerRadius(8)
                }
            }
            .frame(height: 44) // Fixed height to prevent layout shifts
            .padding(.top, 8)
            .padding(.horizontal, 24)

            Spacer()

            // Login Button
            VStack(spacing: 12) {
                Button(action: startBrowserLogin) {
                    HStack(spacing: 8) {
                        if isLoading {
                            ProgressView()
                                .scaleEffect(0.7)
                                .frame(width: 16, height: 16)
                        } else {
                            Image(systemName: "arrow.up.right.square")
                        }
                        Text(isLoading ? "Opening Browser..." : "Login with Browser")
                            .fontWeight(.medium)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 38)
                }
                .buttonStyle(.borderedProminent)
                .disabled(isLoading)
                .padding(.horizontal, 24)

                HStack(spacing: 4) {
                    Text("Need an account?")
                        .foregroundColor(.secondary)
                    Button("Sign up free") {
                        openSignUp()
                    }
                    .buttonStyle(.plain)
                    .foregroundColor(.accentColor)
                }
                .font(.system(size: 12))
            }
            .padding(.bottom, 20)
        }
        .background(Color(nsColor: .windowBackgroundColor))
    }

    private func startBrowserLogin() {
        print("[EnrollmentView] startBrowserLogin called")
        isLoading = true
        errorMessage = nil

        // Generate and store state for CSRF protection
        let state = UUID().uuidString
        UserDefaults.standard.set(state, forKey: Constants.Defaults.authState)
        print("[EnrollmentView] State generated: \(state)")

        // Collect device info to send to auth page
        let deviceInfo = collectDeviceInfo()

        // Build auth URL
        var components = URLComponents(url: Constants.authURL, resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "state", value: state),
            URLQueryItem(name: "device_info", value: deviceInfo),
            URLQueryItem(name: "callback", value: "oximy://auth/callback")
        ]

        if let url = components.url {
            print("[EnrollmentView] Opening URL: \(url.absoluteString)")
            let success = NSWorkspace.shared.open(url)
            print("[EnrollmentView] NSWorkspace.open returned: \(success)")
        } else {
            print("[EnrollmentView] ERROR: Failed to construct URL")
        }

        // Reset loading state after a delay (user is in browser now)
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            isLoading = false
        }
    }

    private func collectDeviceInfo() -> String {
        // Collect device info to send to auth page
        let hostname = Host.current().localizedName ?? "Unknown"
        let osVersion = ProcessInfo.processInfo.operatingSystemVersionString
        let sensorVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"

        let info: [String: String] = [
            "hostname": hostname,
            "os_version": osVersion,
            "sensor_version": sensorVersion
        ]

        // Encode as base64 JSON
        if let jsonData = try? JSONEncoder().encode(info),
           let jsonString = String(data: jsonData, encoding: .utf8) {
            return Data(jsonString.utf8).base64EncodedString()
        }
        return ""
    }

    private func openSignUp() {
        NSWorkspace.shared.open(Constants.signUpURL)
    }
}

// MARK: - Progress Components

struct ProgressDot: View {
    let step: Int
    var isComplete: Bool = false
    var isCurrent: Bool = false

    var body: some View {
        ZStack {
            Circle()
                .fill(backgroundColor)
                .frame(width: 22, height: 22)

            if isComplete {
                Image(systemName: "checkmark")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.white)
            } else {
                Text("\(step)")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(isCurrent ? .white : .secondary)
            }
        }
        .frame(width: 22, height: 22)
        .clipped()
    }

    private var backgroundColor: Color {
        if isComplete {
            return .green
        } else if isCurrent {
            return .accentColor
        } else {
            return .secondary.opacity(0.3)
        }
    }
}

struct ProgressLine: View {
    var isComplete: Bool = false

    var body: some View {
        Rectangle()
            .fill(isComplete ? Color.green : Color.secondary.opacity(0.3))
            .frame(height: 2)
    }
}

#Preview("Enrollment") {
    EnrollmentView()
        .environmentObject(AppState())
        .frame(width: 340, height: 420)
}
