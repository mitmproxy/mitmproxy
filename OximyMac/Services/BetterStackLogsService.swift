import Foundation

@MainActor
final class BetterStackLogsService {
    static let shared = BetterStackLogsService()

    private(set) var isInitialized = false
    private var sourceToken: String?
    private var host: String?
    private var session: URLSession?
    private var buffer: [[String: Any]] = []
    private var flushTimer: Timer?

    private let flushInterval: TimeInterval = 5.0
    private let maxBufferSize = 20

    private init() {}

    func initialize() {
        guard let token = Secrets.betterStackLogsToken, !token.isEmpty,
              let host = Secrets.betterStackLogsHost, !host.isEmpty else {
            print("[BetterStackLogs] No token or host configured - Better Stack Logs disabled")
            return
        }

        self.sourceToken = token
        self.host = host

        // Create a URLSession that bypasses mitmproxy
        let config = URLSessionConfiguration.default
        config.connectionProxyDictionary = [:]
        self.session = URLSession(configuration: config)

        isInitialized = true

        flushTimer = Timer.scheduledTimer(withTimeInterval: flushInterval, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.flush()
            }
        }

        print("[BetterStackLogs] Initialized successfully")
    }

    func enqueue(_ entry: [String: Any]) {
        guard isInitialized else { return }

        buffer.append(entry)

        if buffer.count >= maxBufferSize {
            flush()
        }
    }

    func flush() {
        guard isInitialized, !buffer.isEmpty else { return }
        guard let session = session, let host = host, let token = sourceToken else { return }

        let entries = buffer
        buffer = []

        guard let url = URL(string: host),
              let jsonData = try? JSONSerialization.data(withJSONObject: entries, options: []) else {
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = jsonData

        session.dataTask(with: request) { _, _, error in
            if let error = error {
                // Fail-open: log locally but don't propagate
                NSLog("[BetterStackLogs] Flush failed: %@", error.localizedDescription)
            }
        }.resume()
    }

    func close() {
        flushTimer?.invalidate()
        flushTimer = nil
        flush()
    }
}
