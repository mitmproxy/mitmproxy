import SwiftUI

struct LoginView: View {
    @EnvironmentObject var appState: AppState
    @State private var codeDigits: [String] = Array(repeating: "", count: 6)
    @State private var isValidating = false
    @State private var errorMessage: String?
    @FocusState private var focusedField: Int?

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            // Header
            VStack(spacing: 12) {
                Image(systemName: "link.circle")
                    .font(.system(size: 48))
                    .foregroundColor(.accentColor)

                Text("Connect Your Workspace")
                    .font(.title2)
                    .fontWeight(.semibold)

                Text("Enter the 6-digit code from your Oximy Dashboard")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding(.horizontal, 24)

            Spacer()

            // 6-Digit Code Input
            HStack(spacing: 8) {
                ForEach(0..<6, id: \.self) { index in
                    SingleDigitField(
                        text: $codeDigits[index],
                        isFocused: focusedField == index,
                        onCommit: {
                            if index < 5 {
                                focusedField = index + 1
                            } else {
                                validateCode()
                            }
                        },
                        onBackspace: {
                            if codeDigits[index].isEmpty && index > 0 {
                                focusedField = index - 1
                            }
                        }
                    )
                    .focused($focusedField, equals: index)
                }
            }
            .padding(.horizontal, 24)

            // Error Message
            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
                    .padding(.top, 8)
            }

            Spacer()

            // Sign Up Promo - More prominent
            VStack(spacing: 12) {
                Divider()
                    .padding(.horizontal, 24)

                VStack(spacing: 8) {
                    Text("New to Oximy?")
                        .font(.headline)
                        .foregroundColor(.primary)

                    Text("Create your free account to start tracking AI usage across all your apps.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 16)

                    Button(action: {
                        NSWorkspace.shared.open(Constants.signUpURL)
                    }) {
                        HStack {
                            Text("Sign Up Free")
                            Image(systemName: "arrow.up.right")
                                .font(.caption)
                        }
                        .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.large)
                    .padding(.horizontal, 24)
                    .padding(.top, 4)
                }
            }
            .padding(.bottom, 24)
        }
        .background(Color(nsColor: .windowBackgroundColor))
        .onAppear {
            focusedField = 0
        }
        .overlay {
            if isValidating {
                Color.black.opacity(0.3)
                ProgressView()
                    .progressViewStyle(.circular)
            }
        }
    }

    private var fullCode: String {
        codeDigits.joined()
    }

    private func validateCode() {
        guard fullCode.count == 6 else { return }

        isValidating = true
        errorMessage = nil

        // TODO: Replace with real API call
        // For now, accept any 6-digit code
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            isValidating = false

            // Stub: Accept any code
            appState.completeLogin(
                workspaceName: "Oximy Team",
                deviceToken: "stub-token-\(fullCode)"
            )
        }
    }
}

struct SingleDigitField: View {
    @Binding var text: String
    let isFocused: Bool
    let onCommit: () -> Void
    let onBackspace: () -> Void

    var body: some View {
        TextField("", text: $text)
            .textFieldStyle(.plain)
            .font(.system(size: 24, weight: .medium, design: .monospaced))
            .multilineTextAlignment(.center)
            .frame(width: 40, height: 48)
            .background(Color(nsColor: .controlBackgroundColor))
            .cornerRadius(8)
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(isFocused ? Color.accentColor : Color.gray.opacity(0.3), lineWidth: isFocused ? 2 : 1)
            )
            .onChange(of: text) { newValue in
                // Only allow digits
                let filtered = newValue.filter { $0.isNumber }

                if filtered.isEmpty && !newValue.isEmpty {
                    // User deleted - trigger backspace if field was already empty
                    text = ""
                } else if filtered.isEmpty {
                    text = ""
                    onBackspace()
                } else {
                    // Take only the last digit entered
                    text = String(filtered.suffix(1))
                    onCommit()
                }
            }
    }
}

#Preview {
    LoginView()
        .environmentObject(AppState())
        .frame(width: 320, height: 400)
}
