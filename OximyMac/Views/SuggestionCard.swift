import SwiftUI
import AppKit

struct SuggestionCard: View {
    let suggestion: PlaybookSuggestion
    let onUse: () -> Void
    let onDismiss: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header
            HStack(spacing: 6) {
                Image(systemName: "lightbulb.fill")
                    .foregroundColor(.yellow)
                    .font(.caption)
                Text("Suggested Playbook")
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)
                Spacer()
                // Dismiss X button
                Button(action: onDismiss) {
                    Image(systemName: "xmark")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }

            // Card content
            VStack(alignment: .leading, spacing: 10) {
                // Playbook name + category badge
                HStack(spacing: 8) {
                    Image(systemName: categoryIcon)
                        .foregroundColor(categoryColor)
                        .font(.body)

                    Text(suggestion.playbook.name)
                        .font(.system(size: 13, weight: .semibold))
                        .lineLimit(1)

                    Spacer()

                    // Category badge
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
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(2)

                // Match reason
                Text("Matches your recent prompt")
                    .font(.caption2)
                    .italic()
                    .foregroundColor(.secondary.opacity(0.8))

                // Action buttons
                HStack(spacing: 8) {
                    Button(action: {
                        copyToClipboard(suggestion.playbook.promptTemplate)
                        onUse()
                    }) {
                        HStack(spacing: 4) {
                            Image(systemName: "doc.on.clipboard")
                                .font(.caption2)
                            Text("Use This")
                                .font(.caption)
                                .fontWeight(.medium)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 6)
                        .background(Color.accentColor)
                        .foregroundColor(.white)
                        .cornerRadius(6)
                    }
                    .buttonStyle(.plain)

                    Button(action: onDismiss) {
                        Text("Dismiss")
                            .font(.caption)
                            .fontWeight(.medium)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 6)
                            .background(Color(nsColor: .controlBackgroundColor))
                            .foregroundColor(.secondary)
                            .cornerRadius(6)
                            .overlay(
                                RoundedRectangle(cornerRadius: 6)
                                    .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
                            )
                    }
                    .buttonStyle(.plain)
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
            .padding(10)
            .background(Color(nsColor: .controlBackgroundColor))
            .cornerRadius(8)
        }
        .padding(.horizontal, 16)
        .padding(.top, 12)
        .padding(.bottom, 4)
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

    // MARK: - Clipboard

    private func copyToClipboard(_ text: String) {
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(text, forType: .string)
    }
}
