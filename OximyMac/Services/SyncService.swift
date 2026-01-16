import AppKit
import Foundation

/// Reads the Python addon's upload state (simple format: {filepath: lastLine})
struct AddonUploadState {
    var files: [String: Int]  // filepath -> last uploaded line

    static var fileURL: URL {
        Constants.oximyDir.appendingPathComponent("upload-state.json")
    }

    static func load() -> AddonUploadState {
        guard let data = try? Data(contentsOf: fileURL),
              let dict = try? JSONSerialization.jsonObject(with: data) as? [String: Int]
        else { return AddonUploadState(files: [:]) }
        return AddonUploadState(files: dict)
    }

    func lastSyncedLine(for filepath: String) -> Int {
        files[filepath] ?? 0
    }
}

@MainActor
final class SyncService: ObservableObject {
    static let shared = SyncService()

    enum SyncStatus: Equatable {
        case idle
        case syncing
        case synced
        case offline(retryIn: Int)  // seconds until retry
        case error(String)

        var displayText: String {
            switch self {
            case .idle:
                return "Ready"
            case .syncing:
                return "Syncing..."
            case .synced:
                return "Synced"
            case .offline(let seconds):
                return "Offline - retry in \(seconds)s"
            case .error(let message):
                return message
            }
        }

        var isOffline: Bool {
            if case .offline = self { return true }
            return false
        }
    }

    @Published var isSyncing = false
    @Published var lastSyncTime: Date?
    @Published var pendingEventCount = 0
    @Published var syncError: String?
    @Published var syncStatus: SyncStatus = .idle
    @Published var consecutiveFailures = 0

    private var timer: Timer?

    /// Force sync trigger file - writing this tells the addon to sync immediately
    private static let forceSyncTrigger = Constants.oximyDir.appendingPathComponent("force-sync")

    private var config: DeviceConfig {
        DeviceConfig.load()
    }

    private init() {
        updatePendingCount()
    }

    func start() {
        guard timer == nil else { return }

        SentryService.shared.addStateBreadcrumb(
            category: "sync",
            message: "Sync status monitor started",
            data: ["interval": config.eventFlushIntervalSeconds]
        )

        // Poll for pending count updates (addon handles actual uploads)
        timer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.updatePendingCount()
            }
        }

        // Initial count update
        updatePendingCount()
    }

    func stop() {
        timer?.invalidate()
        timer = nil

        SentryService.shared.addStateBreadcrumb(
            category: "sync",
            message: "Sync status monitor stopped"
        )
    }

    /// Trigger the addon to sync immediately by writing a trigger file
    func syncNow() async {
        isSyncing = true
        syncStatus = .syncing

        // Write trigger file for addon
        do {
            try "sync".write(to: Self.forceSyncTrigger, atomically: true, encoding: .utf8)
            NSLog("[SyncService] Wrote force-sync trigger")

            // Wait briefly for addon to process
            try await Task.sleep(nanoseconds: 500_000_000)  // 0.5s

            // Update pending count after sync
            updatePendingCount()

            lastSyncTime = Date()
            syncStatus = pendingEventCount > 0 ? .idle : .synced
        } catch {
            NSLog("[SyncService] Failed to write force-sync trigger: \(error)")
            syncError = "Failed to trigger sync"
            syncStatus = .error("Trigger failed")
        }

        isSyncing = false
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

    // MARK: - Pending Count (reads addon's upload state)

    private func updatePendingCount() {
        var count = 0
        let addonState = AddonUploadState.load()

        if let files = try? getTraceFiles() {
            for file in files {
                // Addon uses full path as key
                let syncedLine = addonState.lastSyncedLine(for: file.path)
                if let content = try? String(contentsOf: file, encoding: .utf8) {
                    let totalLines = content.components(separatedBy: .newlines).filter { !$0.isEmpty }.count
                    count += max(0, totalLines - syncedLine)
                }
            }
        }

        let previousCount = pendingEventCount
        pendingEventCount = count

        // Update sync status based on count
        if count == 0 && previousCount > 0 {
            lastSyncTime = Date()
            syncStatus = .synced
        } else if count > 0 && syncStatus == .synced {
            syncStatus = .idle
        }
    }

    // MARK: - Sync on Terminate (best effort, synchronous)

    /// Synchronous flush for app termination - triggers addon to sync
    nonisolated func flushSync() {
        // Write trigger file for addon to flush pending traces
        do {
            try "sync".write(to: Self.forceSyncTrigger, atomically: true, encoding: .utf8)
            NSLog("[SyncService] flushSync: wrote force-sync trigger for addon")
            // Give addon a moment to process
            Thread.sleep(forTimeInterval: 0.5)
        } catch {
            NSLog("[SyncService] flushSync: failed to write trigger: \(error)")
        }
    }

    // MARK: - Storage Management

    /// Get total size of local traces in bytes
    func getLocalStorageSize() -> Int64 {
        let fm = FileManager.default
        guard fm.fileExists(atPath: Constants.tracesDir.path) else { return 0 }

        var totalSize: Int64 = 0
        if let files = try? fm.contentsOfDirectory(at: Constants.tracesDir, includingPropertiesForKeys: [.fileSizeKey]) {
            for file in files {
                if let size = try? file.resourceValues(forKeys: [.fileSizeKey]).fileSize {
                    totalSize += Int64(size)
                }
            }
        }
        return totalSize
    }

    /// Get formatted storage size string
    var localStorageSizeFormatted: String {
        let bytes = getLocalStorageSize()
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        return formatter.string(fromByteCount: bytes)
    }

    /// Get count of trace files
    var traceFileCount: Int {
        (try? getTraceFiles().count) ?? 0
    }

    /// Clear all local trace data and sync state
    func clearLocalData() throws {
        let fm = FileManager.default

        // Delete all trace files
        if fm.fileExists(atPath: Constants.tracesDir.path) {
            let files = try fm.contentsOfDirectory(at: Constants.tracesDir, includingPropertiesForKeys: nil)
            for file in files where file.pathExtension == "jsonl" {
                try fm.removeItem(at: file)
            }
        }

        // Clear addon's upload state file
        try? fm.removeItem(at: AddonUploadState.fileURL)

        // Update UI
        pendingEventCount = 0
        syncStatus = .idle
        syncError = nil

        SentryService.shared.addStateBreadcrumb(
            category: "sync",
            message: "Local data cleared by user"
        )
    }

    /// Open traces folder in Finder
    func openTracesFolder() {
        let fm = FileManager.default

        // Ensure directory exists
        if !fm.fileExists(atPath: Constants.tracesDir.path) {
            try? fm.createDirectory(at: Constants.tracesDir, withIntermediateDirectories: true)
        }

        NSWorkspace.shared.selectFile(nil, inFileViewerRootedAtPath: Constants.tracesDir.path)
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
