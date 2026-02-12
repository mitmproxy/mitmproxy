import Foundation
import Sentry

@MainActor
final class OximyLogger {
    static let shared = OximyLogger()

    let sessionId = UUID().uuidString
    private var seq: Int = 0
    private var fileHandle: FileHandle?
    private let logFilePath: URL
    private let maxLogFileSize: Int64 = 50_000_000 // 50MB
    private let maxRotatedFiles = 5

    private var sentryEventCounts: [String: (count: Int, windowStart: Date)] = [:]
    private let maxSentryEventsPerCode = 10
    private let sentryRateWindowSeconds: TimeInterval = 60

    private init() {
        logFilePath = Constants.logsDir.appendingPathComponent("app.jsonl")
        openLogFile()
    }

    func log(
        _ code: EventCode,
        _ message: String,
        data: [String: Any] = [:],
        err: (type: String, code: String, message: String)? = nil
    ) {
        seq += 1
        let now = Date()

        printConsole(code: code, message: message, data: data, timestamp: now)
        writeJSONL(code: code, message: message, data: data, err: err, timestamp: now, seq: seq)
        sendToSentry(code: code, message: message, data: data, err: err)
    }

    private func printConsole(code: EventCode, message: String, data: [String: Any], timestamp: Date) {
        var line = "\(code.levelTag) \(code.rawValue) \(message)"

        if !data.isEmpty {
            let pairs = data.sorted(by: { $0.key < $1.key }).map { "\($0.key)=\($0.value)" }
            line += " | " + pairs.joined(separator: " ")
        }

        NSLog("[Oximy] %@", line)
    }

    private func writeJSONL(
        code: EventCode,
        message: String,
        data: [String: Any],
        err: (type: String, code: String, message: String)?,
        timestamp: Date,
        seq: Int
    ) {
        var entry: [String: Any] = [
            "v": 1,
            "seq": seq,
            "ts": ISO8601DateFormatter.shared.string(from: timestamp),
            "code": code.rawValue,
            "level": code.level.rawValue,
            "svc": code.service,
            "op": code.operation,
            "msg": message,
            "action": code.action.rawValue,
        ]

        var ctx: [String: Any] = ["component": "swift", "session_id": sessionId]
        if let deviceId = UserDefaults.standard.string(forKey: Constants.Defaults.deviceId) {
            ctx["device_id"] = deviceId
        }
        if let workspaceId = UserDefaults.standard.string(forKey: Constants.Defaults.workspaceId) {
            ctx["workspace_id"] = workspaceId
        }
        if let workspaceName = UserDefaults.standard.string(forKey: Constants.Defaults.workspaceName) {
            ctx["workspace_name"] = workspaceName
        }
        entry["ctx"] = ctx

        if !data.isEmpty {
            entry["data"] = data
        }

        if let err = err {
            entry["err"] = ["type": err.type, "code": err.code, "message": err.message]
        }

        guard let jsonData = try? JSONSerialization.data(withJSONObject: entry, options: [.sortedKeys]),
              var jsonLine = String(data: jsonData, encoding: .utf8) else {
            return
        }
        jsonLine += "\n"

        guard let lineData = jsonLine.data(using: .utf8) else { return }

        rotateIfNeeded()
        fileHandle?.write(lineData)
    }

    private func sendToSentry(
        code: EventCode,
        message: String,
        data: [String: Any],
        err: (type: String, code: String, message: String)?
    ) {
        guard SentryService.shared.isInitialized else { return }
        guard code.level >= .info else { return }

        let sentryLevel = code.sentryLevel

        // Always add breadcrumb for info+
        SentryService.shared.addBreadcrumb(
            type: code.level >= .warning ? "error" : "info",
            category: code.service,
            message: "[\(code.rawValue)] \(message)",
            data: data.isEmpty ? nil : data.mapValues { "\($0)" },
            level: sentryLevel
        )

        // Capture Sentry event (rate-limited per event code)
        if shouldSendSentryEvent(code: code.rawValue) {
            SentrySDK.capture(message: "[\(code.rawValue)] \(message)") { scope in
                scope.setLevel(sentryLevel)
                scope.setTag(value: code.rawValue, key: "event_code")
                scope.setTag(value: code.service, key: "service")
                scope.setTag(value: code.operation, key: "operation")
                scope.setTag(value: code.action.rawValue, key: "action_category")

                if let err = err {
                    scope.setTag(value: err.code, key: "error_code")
                }

                if !data.isEmpty {
                    scope.setExtras(data)
                }
            }
        }
    }

    private func shouldSendSentryEvent(code: String) -> Bool {
        let now = Date()

        if let entry = sentryEventCounts[code] {
            if now.timeIntervalSince(entry.windowStart) > sentryRateWindowSeconds {
                sentryEventCounts[code] = (count: 1, windowStart: now)
                return true
            }
            if entry.count >= maxSentryEventsPerCode {
                return false
            }
            sentryEventCounts[code] = (count: entry.count + 1, windowStart: entry.windowStart)
            return true
        }

        sentryEventCounts[code] = (count: 1, windowStart: now)
        return true
    }

    func setTag(_ key: String, value: String) {
        guard SentryService.shared.isInitialized else { return }
        SentrySDK.configureScope { scope in
            scope.setTag(value: value, key: key)
        }
    }

    private func openLogFile() {
        let fm = FileManager.default
        let logsDir = Constants.logsDir
        if !fm.fileExists(atPath: logsDir.path) {
            try? fm.createDirectory(at: logsDir, withIntermediateDirectories: true)
        }
        if !fm.fileExists(atPath: logFilePath.path) {
            fm.createFile(atPath: logFilePath.path, contents: nil)
        }
        fileHandle = try? FileHandle(forWritingTo: logFilePath)
        fileHandle?.seekToEndOfFile()
    }

    func close() {
        fileHandle?.synchronizeFile()
        fileHandle?.closeFile()
        fileHandle = nil
    }

    private func rotateIfNeeded() {
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: logFilePath.path),
              let size = attrs[.size] as? Int64,
              size > maxLogFileSize else {
            return
        }

        fileHandle?.closeFile()
        fileHandle = nil

        let fm = FileManager.default

        for i in stride(from: maxRotatedFiles - 1, through: 1, by: -1) {
            let src = Constants.logsDir.appendingPathComponent("app.\(i).jsonl")
            let dst = Constants.logsDir.appendingPathComponent("app.\(i + 1).jsonl")
            try? fm.removeItem(at: dst)
            try? fm.moveItem(at: src, to: dst)
        }

        let rotatedPath = Constants.logsDir.appendingPathComponent("app.1.jsonl")
        try? fm.removeItem(at: rotatedPath)
        try? fm.moveItem(at: logFilePath, to: rotatedPath)

        openLogFile()
    }
}

private extension ISO8601DateFormatter {
    static let shared: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()
}
