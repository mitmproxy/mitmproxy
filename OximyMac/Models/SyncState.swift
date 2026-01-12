import Foundation

struct SyncState: Codable {
    var files: [String: FileSyncState]

    struct FileSyncState: Codable {
        var lastSyncedLine: Int
        var lastSyncedEventId: String
        var lastSyncTime: Date
    }

    static var empty: SyncState {
        SyncState(files: [:])
    }

    static var fileURL: URL {
        Constants.oximyDir.appendingPathComponent("sync_state.json")
    }

    static func load() -> SyncState {
        guard let data = try? Data(contentsOf: fileURL),
              let state = try? JSONDecoder.iso8601.decode(SyncState.self, from: data)
        else { return .empty }
        return state
    }

    func save() throws {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(self)
        try data.write(to: Self.fileURL, options: .atomic)
    }

    mutating func updateFile(_ filename: String, lastSyncedLine: Int, lastSyncedEventId: String) {
        files[filename] = FileSyncState(
            lastSyncedLine: lastSyncedLine,
            lastSyncedEventId: lastSyncedEventId,
            lastSyncTime: Date()
        )
    }

    func lastSyncedLine(for filename: String) -> Int {
        files[filename]?.lastSyncedLine ?? 0
    }
}

// MARK: - JSONDecoder Extension

extension JSONDecoder {
    static var iso8601: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}
