import SwiftUI

struct OnboardingView: View {
    @EnvironmentObject var appState: AppState
    @State private var currentPage = 0

    private let pages: [(title: String, subtitle: String, systemImage: String?, useLogo: Bool)] = [
        (
            title: "Welcome to Oximy",
            subtitle: "Track your AI usage across every app, invisibly.",
            systemImage: nil,
            useLogo: true  // Show Oximy logo on first page
        ),
        (
            title: "Privacy First",
            subtitle: "Your data stays on your device. We only capture AI interactions you choose to sync.",
            systemImage: "lock.shield",
            useLogo: false
        ),
        (
            title: "Ready to Start",
            subtitle: "Let's set up Oximy to work seamlessly in the background.",
            systemImage: "checkmark.circle",
            useLogo: false
        )
    ]

    var body: some View {
        VStack(spacing: 0) {
            // Content - no TabView, just show current page
            OnboardingPageView(
                title: pages[currentPage].title,
                subtitle: pages[currentPage].subtitle,
                systemImage: pages[currentPage].systemImage,
                useLogo: pages[currentPage].useLogo
            )

            Spacer()

            // Page indicator
            HStack(spacing: 8) {
                ForEach(0..<pages.count, id: \.self) { index in
                    Circle()
                        .fill(index == currentPage ? Color.accentColor : Color.gray.opacity(0.3))
                        .frame(width: 8, height: 8)
                }
            }
            .padding(.bottom, 20)

            // Buttons
            HStack {
                if currentPage > 0 {
                    Button("Back") {
                        withAnimation {
                            currentPage -= 1
                        }
                    }
                    .buttonStyle(.plain)
                    .foregroundColor(.secondary)
                }

                Spacer()

                if currentPage < pages.count - 1 {
                    Button("Next") {
                        withAnimation {
                            currentPage += 1
                        }
                    }
                    .buttonStyle(.borderedProminent)
                } else {
                    Button("Get Started") {
                        appState.completeOnboarding()
                    }
                    .buttonStyle(.borderedProminent)
                }
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 24)
        }
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

struct OnboardingPageView: View {
    let title: String
    let subtitle: String
    let systemImage: String?
    var useLogo: Bool = false

    var body: some View {
        VStack(spacing: 20) {
            Spacer()

            if useLogo {
                OximyLogo(size: 80)
            } else if let systemImage = systemImage {
                Image(systemName: systemImage)
                    .font(.system(size: 64))
                    .foregroundColor(.accentColor)
            }

            Text(title)
                .font(.title)
                .fontWeight(.semibold)
                .multilineTextAlignment(.center)

            Text(subtitle)
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            Spacer()
            Spacer()
        }
    }
}

#Preview {
    OnboardingView()
        .environmentObject(AppState())
        .frame(width: 320, height: 400)
}
