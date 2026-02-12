import Foundation
import Sentry

/// Central structured logger — wraps SentryService + Console + JSONL file output
/// Usage: OximyLogger.shared.log(.MITM_START_002, "mitmproxy listening", data: ["port": 1030])
@MainActor
final class OximyLogger {
    static let shared = OximyLogger()

    /// Session ID for cross-component correlation
    let sessionId = UUID().uuidString

    /// Monotonically increasing sequence number for gap detection
    private var seq: Int = 0

    /// JSONL file handle
    private var fileHandle: FileHandle?
    private let logFilePath: URL
    private let maxLogFileSize: Int64 = 50_000_000 // 50MB
    private let maxRotatedFiles = 5

    private init() {
        logFilePath = Constants.logsDir.appendingPathComponent("app.jsonl")
        openLogFile()
    }

    // MARK: - Public API

    /// Log a structured event
    func log(
        _ code: EventCode,
        _ message: String,
        data: [String: Any] = [:],
        err: (type: String, code: String, message: String)? = nil
    ) {
        seq += 1
        let now = Date()

        // Console output (human-readable)
        printConsole(code: code, message: message, data: data, timestamp: now)

        // JSONL file output (AI-parseable)
        writeJSONL(code: code, message: message, data: data, err: err, timestamp: now, seq: seq)

        // Sentry output (dashboards + alerts)
        sendToSentry(code: code, message: message, data: data, err: err)
    }

    // MARK: - Console Output

    private func printConsole(code: EventCode, message: String, data: [String: Any], timestamp: Date) {
        let levelTag: String
        switch code.level {
        case .debug: levelTag = "[DEBUG]"
        case .info: levelTag = "[INFO] "
        case .warning: levelTag = "[WARN] "
        case .error: levelTag = "[ERROR]"
        case .fatal: levelTag = "[FATAL]"
        }

        var line = "\(levelTag) \(code.rawValue) \(message)"

        if !data.isEmpty {
            let pairs = data.sorted(by: { $0.key < $1.key }).map { "\($0.key)=\($0.value)" }
            line += " | " + pairs.joined(separator: " ")
        }

        NSLog("[Oximy] %@", line)
    }

    // MARK: - JSONL File Output

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

        // Context
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

        // Rotate if needed
        rotateIfNeeded()

        fileHandle?.write(lineData)
    }

    // MARK: - Sentry Output

    private func sendToSentry(
        code: EventCode,
        message: String,
        data: [String: Any],
        err: (type: String, code: String, message: String)?
    ) {
        guard SentryService.shared.isInitialized else { return }

        let sentryLevel: SentryLevel
        switch code.level {
        case .debug: sentryLevel = .debug
        case .info: sentryLevel = .info
        case .warning: sentryLevel = .warning
        case .error: sentryLevel = .error
        case .fatal: sentryLevel = .fatal
        }

        // Always add breadcrumb for info+
        if code.level >= .info {
            let crumb = Breadcrumb()
            crumb.type = code.level >= .warning ? "error" : "info"
            crumb.category = code.service
            crumb.message = "[\(code.rawValue)] \(message)"
            crumb.level = sentryLevel
            if !data.isEmpty {
                crumb.data = data.mapValues { "\($0)" }
            }
            SentrySDK.addBreadcrumb(crumb)
        }

        // Capture Sentry event for warning+
        if code.level >= .warning {
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

    // MARK: - Scope Tags

    /// Update a Sentry scope tag
    func setTag(_ key: String, value: String) {
        guard SentryService.shared.isInitialized else { return }
        SentrySDK.configureScope { scope in
            scope.setTag(value: value, key: key)
        }
    }

    // MARK: - File Management

    private func openLogFile() {
        let fm = FileManager.default

        // Ensure logs directory exists
        let logsDir = Constants.logsDir
        if !fm.fileExists(atPath: logsDir.path) {
            try? fm.createDirectory(at: logsDir, withIntermediateDirectories: true)
        }

        // Create file if needed
        if !fm.fileExists(atPath: logFilePath.path) {
            fm.createFile(atPath: logFilePath.path, contents: nil)
        }

        fileHandle = try? FileHandle(forWritingTo: logFilePath)
        fileHandle?.seekToEndOfFile()
    }

    /// Flush and close the log file handle (call before app exit)
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

        // Shift rotated files: app.4.jsonl → app.5.jsonl, ..., app.1.jsonl → app.2.jsonl
        for i in stride(from: maxRotatedFiles - 1, through: 1, by: -1) {
            let src = Constants.logsDir.appendingPathComponent("app.\(i).jsonl")
            let dst = Constants.logsDir.appendingPathComponent("app.\(i + 1).jsonl")
            try? fm.removeItem(at: dst)
            try? fm.moveItem(at: src, to: dst)
        }

        // Current → app.1.jsonl
        let rotatedPath = Constants.logsDir.appendingPathComponent("app.1.jsonl")
        try? fm.removeItem(at: rotatedPath)
        try? fm.moveItem(at: logFilePath, to: rotatedPath)

        openLogFile()
    }
}

// MARK: - ISO8601 Formatter (thread-safe singleton)

private extension ISO8601DateFormatter {
    static let shared: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()
}
