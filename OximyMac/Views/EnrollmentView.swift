import SwiftUI
import AppKit

struct EnrollmentView: View {
    @EnvironmentObject var appState: AppState

    @State private var digits: [String] = Array(repeating: "", count: 6)
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showSuccess = false
    @FocusState private var focusedIndex: Int?

    private var enrollmentCode: String {
        digits.joined()
    }

    var body: some View {
        VStack(spacing: 0) {
            // Progress indicator - Step 1 of 2
            HStack(spacing: 8) {
                ProgressDot(step: 1, isComplete: showSuccess, isCurrent: !showSuccess)
                ProgressLine(isComplete: showSuccess)
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
                Image(systemName: "number.square.fill")
                    .font(.system(size: 20))
                    .foregroundColor(.accentColor)

                VStack(alignment: .leading, spacing: 1) {
                    Text("Enter your 6-digit code")
                        .font(.system(size: 13, weight: .medium))
                    Text("Find it in your Oximy dashboard")
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

            // Digit Boxes
            HStack(spacing: 8) {
                ForEach(0..<6, id: \.self) { index in
                    DigitField(
                        digit: $digits[index],
                        isFocused: focusedIndex == index,
                        onTap: { focusedIndex = index },
                        onDigitEntered: {
                            if index < 5 {
                                focusedIndex = index + 1
                            } else {
                                focusedIndex = nil
                                if enrollmentCode.count == 6 {
                                    submitCode()
                                }
                            }
                        },
                        onDelete: {
                            if digits[index].isEmpty && index > 0 {
                                focusedIndex = index - 1
                            }
                        }
                    )
                    .focused($focusedIndex, equals: index)
                }
            }
            .padding(.top, 20)
            .padding(.horizontal, 24)

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

            // Submit Button
            VStack(spacing: 12) {
                Button(action: submitCode) {
                    HStack(spacing: 8) {
                        if isLoading {
                            ProgressView()
                                .scaleEffect(0.7)
                                .frame(width: 16, height: 16)
                        } else if showSuccess {
                            Image(systemName: "checkmark.circle.fill")
                        }
                        Text(buttonText)
                            .fontWeight(.medium)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 38)
                }
                .buttonStyle(.borderedProminent)
                .disabled(enrollmentCode.count != 6 || isLoading || showSuccess)
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
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                focusedIndex = 0
            }
        }
    }

    private var buttonText: String {
        if showSuccess {
            return "Connected!"
        } else if isLoading {
            return "Connecting..."
        } else {
            return "Connect"
        }
    }

    private func submitCode() {
        guard enrollmentCode.count == 6, !isLoading else { return }

        isLoading = true
        errorMessage = nil

        Task {
            do {
                let deviceData = try await APIClient.shared.registerDevice(enrollmentCode: enrollmentCode)

                showSuccess = true
                try? await Task.sleep(nanoseconds: 500_000_000)

                appState.login(
                    workspaceName: deviceData.workspaceName ?? deviceData.workspaceId,
                    deviceToken: deviceData.deviceToken
                )
                appState.deviceId = deviceData.deviceId
                appState.completeEnrollment()

                SentryService.shared.addStateBreadcrumb(
                    category: "enrollment",
                    message: "Device enrolled",
                    data: ["deviceId": deviceData.deviceId]
                )

            } catch APIError.invalidEnrollmentCode {
                errorMessage = "Invalid code. Please check and try again."
                clearDigits()
            } catch APIError.enrollmentExpired {
                errorMessage = "Code expired. Get a new one from your dashboard."
                clearDigits()
            } catch APIError.conflict {
                errorMessage = "This device is already registered."
            } catch {
                errorMessage = "Connection failed. Please try again."
            }

            isLoading = false
        }
    }

    private func clearDigits() {
        digits = Array(repeating: "", count: 6)
        focusedIndex = 0
    }

    private func openSignUp() {
        NSWorkspace.shared.open(Constants.signUpURL)
    }
}

// MARK: - Single Digit Field

struct DigitField: View {
    @Binding var digit: String
    let isFocused: Bool
    let onTap: () -> Void
    let onDigitEntered: () -> Void
    let onDelete: () -> Void

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 10)
                .fill(fillColor)

            RoundedRectangle(cornerRadius: 10)
                .stroke(borderColor, lineWidth: isFocused ? 2.5 : 1.5)

            if digit.isEmpty {
                if isFocused {
                    // Blinking cursor
                    Rectangle()
                        .fill(Color.accentColor)
                        .frame(width: 2, height: 24)
                }
            } else {
                Text(digit)
                    .font(.system(size: 28, weight: .bold, design: .rounded))
                    .foregroundColor(.primary)
            }
        }
        .frame(width: 44, height: 54)
        .contentShape(Rectangle())
        .onTapGesture(perform: onTap)
        .background(
            DigitInputHandler(
                digit: $digit,
                isFocused: isFocused,
                onDigitEntered: onDigitEntered,
                onDelete: onDelete
            )
        )
    }

    private var fillColor: Color {
        if !digit.isEmpty {
            return Color.accentColor.opacity(0.1)
        }
        return Color(nsColor: .controlBackgroundColor)
    }

    private var borderColor: Color {
        if isFocused {
            return .accentColor
        } else if !digit.isEmpty {
            return .accentColor.opacity(0.4)
        } else {
            return .secondary.opacity(0.3)
        }
    }
}

// MARK: - Input Handler (NSViewRepresentable for key events)

struct DigitInputHandler: NSViewRepresentable {
    @Binding var digit: String
    let isFocused: Bool
    let onDigitEntered: () -> Void
    let onDelete: () -> Void

    func makeNSView(context: Context) -> KeyCaptureView {
        let view = KeyCaptureView()
        view.onKeyPress = { key in
            handleKey(key)
        }
        return view
    }

    func updateNSView(_ nsView: KeyCaptureView, context: Context) {
        if isFocused {
            DispatchQueue.main.async {
                nsView.window?.makeFirstResponder(nsView)
            }
        }
    }

    private func handleKey(_ key: String) {
        if key == "delete" {
            if digit.isEmpty {
                onDelete()
            } else {
                digit = ""
            }
        } else if key.count == 1, let char = key.first, char.isNumber {
            digit = key
            onDigitEntered()
        }
    }
}

class KeyCaptureView: NSView {
    var onKeyPress: ((String) -> Void)?

    override var acceptsFirstResponder: Bool { true }

    override func keyDown(with event: NSEvent) {
        if event.keyCode == 51 { // Delete key
            onKeyPress?("delete")
        } else if let chars = event.characters {
            onKeyPress?(chars)
        }
    }

    // Handle paste
    @objc func paste(_ sender: Any?) {
        if let string = NSPasteboard.general.string(forType: .string) {
            let digits = string.filter { $0.isNumber }
            for char in digits.prefix(6) {
                onKeyPress?(String(char))
            }
        }
    }

    override func performKeyEquivalent(with event: NSEvent) -> Bool {
        if event.modifierFlags.contains(.command) && event.charactersIgnoringModifiers == "v" {
            paste(nil)
            return true
        }
        return super.performKeyEquivalent(with: event)
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
