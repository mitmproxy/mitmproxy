import Foundation

extension Notification.Name {
    static let violationDetected = Notification.Name("violationDetected")
}

/// Service that polls violations.json written by the Python addon
/// to detect and surface enforcement violations in the Swift UI.
@MainActor
final class ViolationService: ObservableObject {
    static let shared = ViolationService()

    // MARK: - Published State

    @Published var latestViolation: ViolationEntry?
    @Published var showViolationPopover: Bool = false
    @Published var violations: [ViolationEntry] = []
    @Published var isRunning: Bool = false

    // MARK: - Private

    private var timer: Timer?
    private var seenViolationIds: Set<String> = []
    private static let pollInterval: TimeInterval = 1.0
    private static let autoDismissDelay: TimeInterval = 15.0

    static var violationsFilePath: URL {
        Constants.oximyDir.appendingPathComponent("violations.json")
    }

    private init() {
        // Read initial state
        readViolations()
    }

    // MARK: - Start/Stop

    func start() {
        guard !isRunning else { return }
        isRunning = true

        // Initial read
        readViolations()

        // Schedule recurring reads
        timer = Timer.scheduledTimer(withTimeInterval: Self.pollInterval, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.readViolations()
            }
        }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
        isRunning = false
    }

    // MARK: - Violation Reading

    private func readViolations() {
        let fileURL = Self.violationsFilePath

        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            // File doesn't exist yet - addon may not have started
            return
        }

        do {
            let data = try Data(contentsOf: fileURL)
            let decoder = JSONDecoder()
            let state = try decoder.decode(ViolationState.self, from: data)

            violations = state.violations

            // Find new violations we haven't seen before
            let newViolations = state.violations.filter { !seenViolationIds.contains($0.id) }

            if !newViolations.isEmpty {
                // Mark all new IDs as seen
                for violation in newViolations {
                    seenViolationIds.insert(violation.id)
                }

                // Surface the newest unseen violation
                if let newest = newViolations.last {
                    latestViolation = newest
                    showViolationPopover = true

                    print("[ViolationService] New violation detected: \(newest.id) (\(newest.action)) - \(newest.message)")

                    // Post notification for other parts of the app
                    NotificationCenter.default.post(
                        name: .violationDetected,
                        object: newest
                    )

                    // Auto-dismiss after 15 seconds
                    DispatchQueue.main.asyncAfter(deadline: .now() + Self.autoDismissDelay) { [weak self] in
                        self?.showViolationPopover = false
                    }
                }
            }

        } catch {
            // Log but don't crash - file may be in process of being written
            print("[ViolationService] Failed to read violations: \(error)")
        }
    }
}
