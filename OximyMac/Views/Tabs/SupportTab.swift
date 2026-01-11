import SwiftUI

struct SupportTab: View {
    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                // App Info
                VStack(spacing: 8) {
                    Image("Oximy")
                        .resizable()
                        .frame(width: 48, height: 48)
                        .cornerRadius(10)

                    Text("Oximy")
                        .font(.headline)

                    Text("Version 1.0.0")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding()
                .frame(maxWidth: .infinity)
                .background(Color(nsColor: .controlBackgroundColor))
                .cornerRadius(10)

                // Links
                VStack(spacing: 0) {
                    LinkRow(title: "Help & Documentation", icon: "book", url: Constants.helpURL)
                    Divider().padding(.leading, 44)
                    LinkRow(title: "Contact Support", icon: "envelope", url: Constants.supportEmailURL() ?? Constants.helpURL)
                    Divider().padding(.leading, 44)
                    LinkRow(title: "Terms of Service", icon: "doc.text", url: Constants.termsURL)
                    Divider().padding(.leading, 44)
                    LinkRow(title: "Privacy Policy", icon: "hand.raised", url: Constants.privacyURL)
                    Divider().padding(.leading, 44)
                    LinkRow(title: "GitHub", icon: "chevron.left.forwardslash.chevron.right", url: Constants.githubURL)
                }
                .background(Color(nsColor: .controlBackgroundColor))
                .cornerRadius(10)

                // Quit
                Button(role: .destructive) {
                    NotificationCenter.default.post(name: .quitApp, object: nil)
                } label: {
                    Label("Quit Oximy", systemImage: "power")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .padding(.top, 8)
            }
            .padding(16)
        }
    }
}

struct LinkRow: View {
    let title: String
    let icon: String
    let url: URL

    var body: some View {
        Button(action: {
            NSWorkspace.shared.open(url)
        }) {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .frame(width: 24)
                    .foregroundColor(.accentColor)

                Text(title)
                    .foregroundColor(.primary)

                Spacer()

                Image(systemName: "arrow.up.right")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
        }
        .buttonStyle(.plain)
    }
}

#Preview {
    SupportTab()
        .frame(width: 340, height: 400)
}
