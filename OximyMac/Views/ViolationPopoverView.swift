import SwiftUI
import AppKit

// MARK: - Non-activating Panel Infrastructure (Granola / Notion style)

/// Custom NSPanel that accepts mouse clicks without stealing focus from the active app.
class InteractivePanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
}

/// NSHostingView subclass that ensures first-click works on buttons inside non-key panels.
class FirstClickHostingView<Content: View>: NSHostingView<Content> {
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }

    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        let area = NSTrackingArea(
            rect: bounds,
            options: [.mouseEnteredAndExited, .mouseMoved, .activeAlways, .inVisibleRect, .cursorUpdate],
            owner: self,
            userInfo: nil
        )
        addTrackingArea(area)
    }
}

// MARK: - Violation Panel Controller

/// Floating panel that appears when PII is redacted from a request.
/// Non-activating — doesn't steal focus from the user's current app.
@MainActor
final class ViolationPanelController {
    static let shared = ViolationPanelController()

    private var panel: NSPanel?
    private var autoDismissWork: DispatchWorkItem?

    private init() {}

    func show(violation: ViolationEntry) {
        dismiss()

        let panelContent = ViolationPanelView(
            violation: violation,
            onDismiss: { [weak self] in
                self?.dismiss()
            }
        )

        let hostingView = FirstClickHostingView(rootView: AnyView(panelContent))
        hostingView.frame = NSRect(x: 0, y: 0, width: 300, height: 160)

        let panel = InteractivePanel(
            contentRect: NSRect(x: 0, y: 0, width: 300, height: 160),
            styleMask: [.borderless, .nonactivatingPanel, .utilityWindow],
            backing: .buffered,
            defer: false
        )
        panel.isFloatingPanel = true
        panel.level = .floating
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = true
        panel.contentView = hostingView
        panel.isMovableByWindowBackground = true
        panel.hidesOnDeactivate = false
        panel.acceptsMouseMovedEvents = true
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]

        // Position: top-right of screen, below menu bar
        if let screen = NSScreen.main {
            let screenFrame = screen.visibleFrame
            let x = screenFrame.maxX - 300 - 16
            let y = screenFrame.maxY - 160 - 16
            panel.setFrameOrigin(NSPoint(x: x, y: y))
        }

        panel.orderFrontRegardless()

        // Animate in: slide down + fade
        panel.alphaValue = 0
        let finalFrame = panel.frame
        panel.setFrame(
            NSRect(x: finalFrame.origin.x, y: finalFrame.origin.y + 20,
                   width: finalFrame.width, height: finalFrame.height),
            display: false
        )
        NSAnimationContext.runAnimationGroup { context in
            context.duration = 0.3
            context.timingFunction = CAMediaTimingFunction(name: .easeOut)
            panel.animator().alphaValue = 1
            panel.animator().setFrame(finalFrame, display: true)
        }

        self.panel = panel

        // Auto-dismiss after 10 seconds
        let work = DispatchWorkItem { [weak self] in
            self?.dismiss()
        }
        autoDismissWork = work
        DispatchQueue.main.asyncAfter(deadline: .now() + 10, execute: work)
    }

    func dismiss() {
        autoDismissWork?.cancel()
        autoDismissWork = nil

        guard let panel = panel else { return }

        NSAnimationContext.runAnimationGroup({ context in
            context.duration = 0.2
            context.timingFunction = CAMediaTimingFunction(name: .easeIn)
            panel.animator().alphaValue = 0
        }, completionHandler: { [weak self] in
            panel.orderOut(nil)
            self?.panel = nil
        })
    }
}

// MARK: - SwiftUI View

struct ViolationPanelView: View {
    let violation: ViolationEntry
    let onDismiss: () -> Void

    @State private var closeHovered = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            // Header
            HStack(spacing: 6) {
                Image(systemName: "shield.lefthalf.filled")
                    .foregroundColor(.orange)
                    .font(.system(size: 12))
                Text("Data Redacted")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.secondary)
                Spacer()
                Button(action: onDismiss) {
                    Image(systemName: "xmark")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(closeHovered ? .primary : .secondary)
                        .frame(width: 18, height: 18)
                        .background(closeHovered ? Color.secondary.opacity(0.2) : Color(nsColor: .controlBackgroundColor))
                        .cornerRadius(9)
                }
                .buttonStyle(.plain)
                .onHover { hovering in
                    withAnimation(.easeInOut(duration: 0.15)) { closeHovered = hovering }
                    if hovering { NSCursor.pointingHand.push() } else { NSCursor.pop() }
                }
            }

            // What was detected + where
            HStack(spacing: 8) {
                Image(systemName: piiIcon)
                    .foregroundColor(.orange)
                    .font(.system(size: 14))

                Text(piiLabel)
                    .font(.system(size: 13, weight: .semibold))
                    .lineLimit(1)

                Spacer()

                Text(violation.host)
                    .font(.system(size: 10, weight: .medium))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.blue.opacity(0.15))
                    .foregroundColor(.blue)
                    .cornerRadius(4)
                    .lineLimit(1)
            }

            // Description
            Text("Replaced with [\(redactLabel)_REDACTED] before reaching the AI provider.")
                .font(.system(size: 11))
                .foregroundColor(.secondary)
                .lineLimit(2)

            // Footer
            HStack(spacing: 4) {
                Image(systemName: "checkmark.shield.fill")
                    .font(.system(size: 9))
                    .foregroundColor(.green.opacity(0.7))
                Text("Sensitive data never left your device")
                    .font(.system(size: 10))
                    .foregroundColor(.secondary.opacity(0.6))
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(nsColor: .windowBackgroundColor))
                .shadow(color: .black.opacity(0.2), radius: 12, x: 0, y: 4)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.secondary.opacity(0.15), lineWidth: 1)
        )
    }

    // MARK: - PII type styling

    private var piiLabel: String {
        violation.detectedType
            .replacingOccurrences(of: "_", with: " ")
            .capitalized
    }

    private var redactLabel: String {
        // First type only for the placeholder label
        let first = violation.detectedType
            .components(separatedBy: ",")
            .first?
            .trimmingCharacters(in: .whitespaces) ?? violation.detectedType
        return first.uppercased()
    }

    private var piiIcon: String {
        let type = violation.detectedType.lowercased()
        if type.contains("email") { return "envelope.fill" }
        if type.contains("credit") || type.contains("card") { return "creditcard.fill" }
        if type.contains("ssn") { return "person.text.rectangle.fill" }
        if type.contains("phone") { return "phone.fill" }
        if type.contains("api_key") || type.contains("token") { return "key.fill" }
        return "shield.lefthalf.filled.trianglebadge.exclamationmark"
    }
}
