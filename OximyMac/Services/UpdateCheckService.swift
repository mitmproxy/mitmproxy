import Foundation

/// Checks for app updates by fetching version.json from GitHub Releases.
/// Respects MDM-managed deployments by skipping the check entirely.
@MainActor
final class UpdateCheckService: ObservableObject {
    static let shared = UpdateCheckService()

    @Published var updateAvailable = false
    @Published var unsupported = false
    @Published var latestVersion: String?
    @Published var downloadURL: URL?

    private static let versionCheckURL = URL(string: "https://github.com/OximyHQ/sensor/releases/download/latest/version.json")!

    private var hasChecked = false

    private init() {}

    /// Check for updates on app launch. Fails silently — never blocks the app.
    func checkOnce() {
        guard !hasChecked else { return }
        hasChecked = true

        // Skip update checks for MDM-managed devices
        if MDMConfigService.shared.isManagedDevice {
            return
        }

        Task {
            await check()
        }
    }

    private func check() async {
        var request = URLRequest(url: Self.versionCheckURL)
        request.timeoutInterval = 10
        request.cachePolicy = .reloadIgnoringLocalCacheData

        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                return
            }

            let info = try JSONDecoder().decode(VersionInfo.self, from: data)
            let currentVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.0.0"

            if compareVersions(currentVersion, info.minSupported) == .orderedAscending {
                // Below minimum supported version
                latestVersion = info.latest
                downloadURL = URL(string: info.download.macos)
                unsupported = true
                updateAvailable = true
            } else if compareVersions(currentVersion, info.latest) == .orderedAscending {
                // Update available but not critical
                latestVersion = info.latest
                downloadURL = URL(string: info.download.macos)
                updateAvailable = true
            }
        } catch {
            // Fail silently — update check is best-effort
        }
    }

    /// Semantic version comparison
    private func compareVersions(_ a: String, _ b: String) -> ComparisonResult {
        let aParts = a.split(separator: ".").map { Int($0) ?? 0 }
        let bParts = b.split(separator: ".").map { Int($0) ?? 0 }
        let maxLen = max(aParts.count, bParts.count)

        for i in 0..<maxLen {
            let aVal = i < aParts.count ? aParts[i] : 0
            let bVal = i < bParts.count ? bParts[i] : 0
            if aVal < bVal { return .orderedAscending }
            if aVal > bVal { return .orderedDescending }
        }
        return .orderedSame
    }
}

// MARK: - JSON Model

private struct VersionInfo: Decodable {
    let latest: String
    let minSupported: String
    let download: Download

    struct Download: Decodable {
        let macos: String
        let windows: String
    }

    enum CodingKeys: String, CodingKey {
        case latest
        case minSupported = "min_supported"
        case download
    }
}
