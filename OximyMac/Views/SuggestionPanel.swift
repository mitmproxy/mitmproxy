import SwiftUI
import AppKit

/// Custom NSPanel that accepts mouse clicks without stealing focus from the active app.
/// This is the standard pattern for interactive floating panels (like Notion Calendar, Granola).
class InteractivePanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
}

/// NSHostingView subclass that ensures first-click works on buttons inside non-key panels.
class FirstClickHostingView<Content: View>: NSHostingView<Content> {
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }

    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        // Remove old tracking areas to prevent accumulation
        for existing in trackingAreas {
            removeTrackingArea(existing)
        }
        // Ensure cursor updates work even when the window isn't key
        let area = NSTrackingArea(
            rect: bounds,
            options: [.mouseEnteredAndExited, .mouseMoved, .activeAlways, .inVisibleRect, .cursorUpdate],
            owner: self,
            userInfo: nil
        )
        addTrackingArea(area)
    }

}

/// A floating panel that appears on screen when a playbook suggestion is detected.
/// Non-activating — doesn't steal focus from the user's current app.
/// Similar to Notion Calendar's "Join Meeting" or Granola's floating widget.
@MainActor
final class SuggestionPanelController {
    static let shared = SuggestionPanelController()

    private var panel: NSPanel?
    private var hostingView: NSHostingView<AnyView>?

    private init() {}

    func show(suggestion: PlaybookSuggestion) {
        // Dismiss any existing panel
        dismiss()

        let panelContent = SuggestionPanelView(
            suggestion: suggestion,
            onUse: { [weak self] in
                SuggestionService.shared.useSuggestion()
                self?.dismiss()
            },
            onDismiss: { [weak self] in
                SuggestionService.shared.dismissSuggestion()
                self?.dismiss()
            }
        )

        let hostingView = FirstClickHostingView(rootView: AnyView(panelContent))
        hostingView.frame = NSRect(x: 0, y: 0, width: 320, height: 220)

        // Borderless, floating, non-activating panel that accepts clicks
        let panel = InteractivePanel(
            contentRect: NSRect(x: 0, y: 0, width: 320, height: 220),
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
            let x = screenFrame.maxX - 320 - 16
            let y = screenFrame.maxY - 220 - 16
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
        self.hostingView = hostingView

        // Auto-dismiss after 30 seconds if not interacted with
        DispatchQueue.main.asyncAfter(deadline: .now() + 30) { [weak self] in
            if self?.panel != nil {
                SuggestionService.shared.dismissSuggestion()
                self?.dismiss()
            }
        }
    }

    func dismiss() {
        guard let panel = panel else { return }

        NSAnimationContext.runAnimationGroup({ context in
            context.duration = 0.2
            context.timingFunction = CAMediaTimingFunction(name: .easeIn)
            panel.animator().alphaValue = 0
        }, completionHandler: { [weak self] in
            panel.orderOut(nil)
            self?.panel = nil
            self?.hostingView = nil
        })
    }
}

// MARK: - SwiftUI View for the floating panel

struct SuggestionPanelView: View {
    let suggestion: PlaybookSuggestion
    let onUse: () -> Void
    let onDismiss: () -> Void

    @State private var copied = false
    @State private var useHovered = false
    @State private var dismissHovered = false
    @State private var closeHovered = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            // Header row
            HStack(spacing: 6) {
                Image(systemName: "lightbulb.fill")
                    .foregroundColor(.yellow)
                    .font(.system(size: 12))
                Text("Suggested Playbook")
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

            // Playbook name + category
            HStack(spacing: 8) {
                Image(systemName: categoryIcon)
                    .foregroundColor(categoryColor)
                    .font(.system(size: 14))

                Text(suggestion.playbook.name)
                    .font(.system(size: 13, weight: .semibold))
                    .lineLimit(1)

                Spacer()

                Text(suggestion.playbook.category.capitalized)
                    .font(.system(size: 10, weight: .medium))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(categoryColor.opacity(0.15))
                    .foregroundColor(categoryColor)
                    .cornerRadius(4)
            }

            // Description
            Text(suggestion.playbook.description)
                .font(.system(size: 11))
                .foregroundColor(.secondary)
                .lineLimit(2)

            // Buttons
            HStack(spacing: 8) {
                Button(action: {
                    guard !copied else { return }
                    copyToClipboard(suggestion.playbook.promptTemplate)
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.6)) {
                        copied = true
                    }
                    // Dismiss after showing success
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                        onUse()
                    }
                }) {
                    HStack(spacing: 4) {
                        Image(systemName: copied ? "checkmark" : "doc.on.clipboard")
                            .font(.system(size: 10, weight: copied ? .bold : .regular))
                        Text(copied ? "Copied!" : "Copy & Use")
                            .font(.system(size: 11, weight: .medium))
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 7)
                    .background(copied ? Color.green : (useHovered ? Color.accentColor.opacity(0.85) : Color.accentColor))
                    .foregroundColor(.white)
                    .cornerRadius(6)
                    .scaleEffect(copied ? 1.03 : 1.0)
                }
                .buttonStyle(.plain)
                .onHover { hovering in
                    withAnimation(.easeInOut(duration: 0.15)) { useHovered = hovering }
                    if hovering { NSCursor.pointingHand.push() } else { NSCursor.pop() }
                }

                Button(action: onDismiss) {
                    Text("Dismiss")
                        .font(.system(size: 11, weight: .medium))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 7)
                        .background(dismissHovered ? Color.secondary.opacity(0.15) : Color(nsColor: .controlBackgroundColor))
                        .foregroundColor(dismissHovered ? .primary : .secondary)
                        .cornerRadius(6)
                        .overlay(
                            RoundedRectangle(cornerRadius: 6)
                                .stroke(Color.secondary.opacity(dismissHovered ? 0.3 : 0.2), lineWidth: 1)
                        )
                }
                .buttonStyle(.plain)
                .onHover { hovering in
                    withAnimation(.easeInOut(duration: 0.15)) { dismissHovered = hovering }
                    if hovering { NSCursor.pointingHand.push() } else { NSCursor.pop() }
                }
            }

            // Trust footer
            HStack(spacing: 4) {
                Image(systemName: "checkmark.shield.fill")
                    .font(.system(size: 9))
                    .foregroundColor(.green.opacity(0.7))
                Text("Approved by your organization")
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

    // MARK: - Category Styling

    private var categoryIcon: String {
        switch suggestion.playbook.category {
        case "coding": return "chevron.left.forwardslash.chevron.right"
        case "writing": return "doc.text"
        case "analysis": return "chart.bar"
        case "research": return "magnifyingglass"
        default: return "star"
        }
    }

    private var categoryColor: Color {
        switch suggestion.playbook.category {
        case "coding": return .blue
        case "writing": return .purple
        case "analysis": return .orange
        case "research": return .teal
        default: return .gray
        }
    }

    private func copyToClipboard(_ text: String) {
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(text, forType: .string)
    }
}
