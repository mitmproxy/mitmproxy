import Foundation

@MainActor
final class SyncService: ObservableObject {
    static let shared = SyncService()

    @Published var isSyncing = false
    @Published var lastSyncTime: Date?
    @Published var pendingEventCount = 0
    @Published var syncError: String?

    private var timer: Timer?
    private var syncState: SyncState

    private var config: DeviceConfig {
        DeviceConfig.load()
    }

    private init() {
        syncState = SyncState.load()
        updatePendingCount()
    }

    func start() {
        guard timer == nil else { return }

        SentryService.shared.addStateBreadcrumb(
            category: "sync",
            message: "Sync service started",
            data: ["interval": config.eventFlushIntervalSeconds]
        )

        // Schedule recurring sync
        timer = Timer.scheduledTimer(withTimeInterval: TimeInterval(config.eventFlushIntervalSeconds), repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                await self?.syncAllEvents()
            }
        }

        // Trigger initial sync
        Task { await syncAllEvents() }
    }

    func stop() {
        timer?.invalidate()
        timer = nil

        SentryService.shared.addStateBreadcrumb(
            category: "sync",
            message: "Sync service stopped"
        )
    }

    func syncNow() async {
        await syncAllEvents()
    }

    /// Sync ALL pending events in this cycle to prevent backlog
    private func syncAllEvents() async {
        guard APIClient.shared.isAuthenticated, !isSyncing else { return }

        isSyncing = true
        defer {
            isSyncing = false
            updatePendingCount()
        }

        do {
            // Reload sync state in case it was modified
            syncState = SyncState.load()

            // Get all trace files sorted by date
            let traceFiles = try getTraceFiles()

            var totalSynced = 0

            for file in traceFiles {
                let synced = try await syncFile(file)
                totalSynced += synced
            }

            if totalSynced > 0 {
                lastSyncTime = Date()
                syncError = nil

                SentryService.shared.addStateBreadcrumb(
                    category: "sync",
                    message: "Events synced",
                    data: ["count": totalSynced]
                )
            }

        } catch APIError.unauthorized {
            // Auth failure handled by APIClient
            syncError = "Authentication failed"
        } catch {
            syncError = error.localizedDescription

            SentryService.shared.addErrorBreadcrumb(
                service: "sync",
                error: error.localizedDescription
            )
        }
    }

    /// Sync a single file, sending ALL unsynced events in batches
    /// Returns number of events synced
    private func syncFile(_ fileURL: URL) async throws -> Int {
        let filename = fileURL.lastPathComponent
        let lastSyncedLine = syncState.lastSyncedLine(for: filename)

        // Read all unsynced lines
        let lines = try readLines(from: fileURL, startingAt: lastSyncedLine)

        guard !lines.isEmpty else { return 0 }

        var totalSynced = 0
        var currentLine = lastSyncedLine

        // Chunk into batches and send ALL of them sequentially
        let batches = lines.chunked(into: config.eventBatchSize)

        for batch in batches {
            let events = batch.compactMap { parseEvent($0) }

            guard !events.isEmpty else {
                currentLine += batch.count
                continue
            }

            // Send this batch
            let response = try await APIClient.shared.submitEvents(events)

            // Update sync state after each successful batch
            currentLine += batch.count
            let lastEventId = extractEventId(from: batch.last ?? "") ?? ""

            syncState.updateFile(filename, lastSyncedLine: currentLine, lastSyncedEventId: lastEventId)
            try syncState.save()

            totalSynced += response.accepted
        }

        return totalSynced
    }

    // MARK: - File Reading

    private func getTraceFiles() throws -> [URL] {
        let fm = FileManager.default

        // Ensure traces directory exists
        if !fm.fileExists(atPath: Constants.tracesDir.path) {
            return []
        }

        let contents = try fm.contentsOfDirectory(
            at: Constants.tracesDir,
            includingPropertiesForKeys: [.contentModificationDateKey]
        )

        return contents
            .filter { $0.pathExtension == "jsonl" && $0.lastPathComponent.hasPrefix("traces_") }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
    }

    private func readLines(from url: URL, startingAt line: Int) throws -> [String] {
        let content = try String(contentsOf: url, encoding: .utf8)
        let allLines = content.components(separatedBy: .newlines).filter { !$0.isEmpty }
        return Array(allLines.dropFirst(line))
    }

    private func parseEvent(_ line: String) -> JSONValue? {
        guard let data = line.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else { return nil }

        return JSONValue(from: json)
    }

    private func extractEventId(from line: String) -> String? {
        guard let data = line.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let eventId = json["event_id"] as? String
        else { return nil }
        return eventId
    }

    // MARK: - Pending Count

    private func updatePendingCount() {
        Task {
            var count = 0
            if let files = try? getTraceFiles() {
                for file in files {
                    let filename = file.lastPathComponent
                    let syncedLine = syncState.lastSyncedLine(for: filename)
                    if let content = try? String(contentsOf: file, encoding: .utf8) {
                        let totalLines = content.components(separatedBy: .newlines).filter { !$0.isEmpty }.count
                        count += max(0, totalLines - syncedLine)
                    }
                }
            }
            pendingEventCount = count
        }
    }

    // MARK: - Sync on Terminate (best effort, synchronous)

    /// Synchronous flush for app termination - blocks until complete or timeout
    /// Uses a background thread to avoid MainActor deadlock
    nonisolated func flushSync() {
        let deviceToken = UserDefaults.standard.string(forKey: Constants.Defaults.deviceToken)
        guard let token = deviceToken else { return }

        // Load sync state and config synchronously
        let syncState = SyncState.load()
        let config = DeviceConfig.load()
        let apiEndpoint = config.apiEndpoint

        // Get pending events synchronously
        let fm = FileManager.default
        guard fm.fileExists(atPath: Constants.tracesDir.path),
              let files = try? fm.contentsOfDirectory(at: Constants.tracesDir, includingPropertiesForKeys: nil)
                .filter({ $0.pathExtension == "jsonl" && $0.lastPathComponent.hasPrefix("traces_") })
        else { return }

        var allEvents: [JSONValue] = []
        var mutableSyncState = syncState

        for file in files {
            let filename = file.lastPathComponent
            let lastSyncedLine = syncState.lastSyncedLine(for: filename)

            guard let content = try? String(contentsOf: file, encoding: .utf8) else { continue }
            let lines = content.components(separatedBy: .newlines).filter { !$0.isEmpty }
            let unsyncedLines = Array(lines.dropFirst(lastSyncedLine))

            for line in unsyncedLines {
                if let data = line.data(using: .utf8),
                   let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    allEvents.append(JSONValue(from: json))
                }
            }

            // Update sync state to mark all as synced (optimistically)
            if !unsyncedLines.isEmpty {
                mutableSyncState.updateFile(filename, lastSyncedLine: lines.count, lastSyncedEventId: "")
            }
        }

        guard !allEvents.isEmpty else { return }

        // Send synchronously with timeout
        let semaphore = DispatchSemaphore(value: 0)
        var success = false

        // Batch events (max 100 per request as per API)
        let batches = allEvents.chunked(into: config.eventBatchSize)

        for batch in batches {
            guard let url = URL(string: apiEndpoint)?.appendingPathComponent("devices/events"),
                  let body = try? JSONEncoder().encode(EventBatchRequest(events: batch))
            else { continue }

            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            request.httpBody = body
            request.timeoutInterval = 5 // Short timeout for termination

            let task = URLSession.shared.dataTask(with: request) { _, response, _ in
                if let httpResponse = response as? HTTPURLResponse,
                   httpResponse.statusCode == 200 || httpResponse.statusCode == 201 {
                    success = true
                }
                semaphore.signal()
            }
            task.resume()

            // Wait up to 5 seconds per batch
            _ = semaphore.wait(timeout: .now() + 5)
        }

        // Save sync state if successful
        if success {
            try? mutableSyncState.save()
            NSLog("[SyncService] flushSync: synced \(allEvents.count) events on termination")
        }
    }
}

// MARK: - Array Chunking Extension

extension Array {
    func chunked(into size: Int) -> [[Element]] {
        guard size > 0 else { return [self] }
        return stride(from: 0, to: count, by: size).map {
            Array(self[$0..<Swift.min($0 + size, count)])
        }
    }
}
