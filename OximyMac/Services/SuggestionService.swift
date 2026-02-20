import Foundation

extension Notification.Name {
    static let newSuggestionAvailable = Notification.Name("newSuggestionAvailable")
}

/// Polls ~/.oximy/suggestions.json for proactive playbook suggestions
/// written by the Python mitmproxy addon.
@MainActor
final class SuggestionService: ObservableObject {
    static let shared = SuggestionService()

    // MARK: - Published State

    @Published var currentSuggestion: PlaybookSuggestion?

    // MARK: - Private

    private var timer: Timer?
    private static let pollInterval: TimeInterval = 2.0

    /// IDs we've already shown (dismissed or used) — don't re-surface them
    private var seenIds: Set<String> = []

    /// Last ID we read from disk (avoid re-parsing unchanged file)
    private var lastReadId: String?

    static var suggestionsFilePath: URL {
        Constants.oximyDir.appendingPathComponent("suggestions.json")
    }

    private init() {}

    // MARK: - Start / Stop

    func start() {
        print("[SuggestionService] Starting — watching \(Self.suggestionsFilePath.path)")

        // Initial read
        readSuggestion()

        // Poll every 2 seconds
        timer = Timer.scheduledTimer(withTimeInterval: Self.pollInterval, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.readSuggestion()
            }
        }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
    }

    // MARK: - Actions

    /// Mark the current suggestion as used (copies template to clipboard)
    func useSuggestion() {
        guard let suggestion = currentSuggestion else { return }
        seenIds.insert(suggestion.id)
        currentSuggestion = nil
        writeDismissal(id: suggestion.id, action: "used")
    }

    /// Dismiss the current suggestion
    func dismissSuggestion() {
        guard let suggestion = currentSuggestion else { return }
        seenIds.insert(suggestion.id)
        currentSuggestion = nil
        writeDismissal(id: suggestion.id, action: "dismissed")
    }

    // MARK: - File Reading

    private func readSuggestion() {
        let fileURL = Self.suggestionsFilePath

        let exists = FileManager.default.fileExists(atPath: fileURL.path)
        guard exists else {
            return
        }

        do {
            let data = try Data(contentsOf: fileURL)
            let suggestion = try JSONDecoder().decode(PlaybookSuggestion.self, from: data)

            // Skip if already seen or same as current
            guard !seenIds.contains(suggestion.id),
                  suggestion.id != lastReadId else {
                return
            }

            // Only show pending suggestions
            guard suggestion.status == "pending" else {
                print("[SuggestionService] Suggestion \(suggestion.id) status=\(suggestion.status), skipping")
                return
            }

            print("[SuggestionService] New suggestion found: \(suggestion.playbook.name) (id=\(suggestion.id))")
            lastReadId = suggestion.id
            currentSuggestion = suggestion

            // Notify AppDelegate to auto-show the popover
            NotificationCenter.default.post(name: .newSuggestionAvailable, object: nil)

        } catch {
            print("[SuggestionService] Failed to decode: \(error)")
        }
    }

    private func writeDismissal(id: String, action: String) {
        let fileURL = Self.suggestionsFilePath

        // Overwrite the file with updated status so addon knows
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return }

        do {
            let data = try Data(contentsOf: fileURL)
            guard var json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }

            // Only update if it's the same suggestion
            guard json["id"] as? String == id else { return }

            json["status"] = action
            let updated = try JSONSerialization.data(withJSONObject: json, options: [.prettyPrinted])
            try updated.write(to: fileURL)
        } catch {
            print("[SuggestionService] Failed to write dismissal: \(error)")
        }
    }
}
