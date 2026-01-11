import Foundation

// MARK: - Device Registration

struct DeviceRegistrationRequest: Encodable {
    let hostname: String
    let displayName: String?
    let os: String = "mac"
    let osVersion: String
    let sensorVersion: String
    let hardwareId: String
    let ownerEmail: String?
    let permissions: Permissions

    struct Permissions: Encodable {
        let networkCapture: Bool
        let systemExtension: Bool
        let fullDiskAccess: Bool
    }
}

struct DeviceRegistrationResponse: Decodable {
    let success: Bool
    let data: DeviceData?
    let error: APIErrorData?
    let meta: ResponseMeta?

    struct DeviceData: Decodable {
        let deviceId: String
        let deviceName: String
        let deviceToken: String
        let workspaceId: String
        let config: DeviceConfig
    }
}

// MARK: - Device Config

struct DeviceConfig: Codable {
    let heartbeatIntervalSeconds: Int
    let eventBatchSize: Int
    let eventFlushIntervalSeconds: Int
    let apiEndpoint: String

    static var `default`: DeviceConfig {
        DeviceConfig(
            heartbeatIntervalSeconds: 60,
            eventBatchSize: 100,
            eventFlushIntervalSeconds: 5,
            apiEndpoint: Constants.defaultAPIEndpoint
        )
    }

    func save() {
        let defaults = UserDefaults.standard
        defaults.set(heartbeatIntervalSeconds, forKey: Constants.Defaults.heartbeatInterval)
        defaults.set(eventBatchSize, forKey: Constants.Defaults.eventBatchSize)
        defaults.set(eventFlushIntervalSeconds, forKey: Constants.Defaults.eventFlushInterval)
        defaults.set(apiEndpoint, forKey: Constants.Defaults.apiEndpoint)
    }

    static func load() -> DeviceConfig {
        let defaults = UserDefaults.standard
        return DeviceConfig(
            heartbeatIntervalSeconds: defaults.integer(forKey: Constants.Defaults.heartbeatInterval).nonZero ?? 60,
            eventBatchSize: defaults.integer(forKey: Constants.Defaults.eventBatchSize).nonZero ?? 100,
            eventFlushIntervalSeconds: defaults.integer(forKey: Constants.Defaults.eventFlushInterval).nonZero ?? 5,
            apiEndpoint: defaults.string(forKey: Constants.Defaults.apiEndpoint) ?? Constants.defaultAPIEndpoint
        )
    }
}

// MARK: - Heartbeat

struct HeartbeatRequest: Encodable {
    let sensorVersion: String
    let uptimeSeconds: Int
    let permissions: DeviceRegistrationRequest.Permissions
    let metrics: Metrics?

    struct Metrics: Encodable {
        let cpuPercent: Double?
        let memoryMb: Int?
        let eventsQueued: Int
    }
}

struct HeartbeatResponse: Decodable {
    let success: Bool
    let data: HeartbeatData?
    let error: APIErrorData?
    let meta: ResponseMeta?

    struct HeartbeatData: Decodable {
        let status: String
        let configUpdate: DeviceConfig?
        let commands: [String]?
    }
}

// MARK: - Events

struct EventBatchRequest: Encodable {
    let events: [JSONValue]
}

struct EventBatchResponse: Decodable {
    let success: Bool
    let data: EventData?
    let error: APIErrorData?
    let meta: ResponseMeta?

    struct EventData: Decodable {
        let accepted: Int
        let rejected: Int
        let deviceId: String
    }
}

// MARK: - Common

struct APIErrorData: Decodable {
    let code: String
    let message: String
}

struct ResponseMeta: Decodable {
    let requestId: String
    let timestamp: String
}

// MARK: - API Error

enum APIError: LocalizedError {
    case networkUnavailable
    case invalidEnrollmentCode
    case enrollmentExpired
    case unauthorized
    case deviceNotFound
    case conflict(String)
    case serverError(Int, String)
    case encodingError
    case decodingError(String)
    case rateLimited(retryAfter: Int?)

    var errorDescription: String? {
        switch self {
        case .networkUnavailable:
            return "No internet connection"
        case .invalidEnrollmentCode:
            return "Invalid or expired enrollment code"
        case .enrollmentExpired:
            return "Enrollment code has expired"
        case .unauthorized:
            return "Session expired. Please reconnect."
        case .deviceNotFound:
            return "Device not found. It may have been removed."
        case .conflict(let msg):
            return "Device already registered: \(msg)"
        case .serverError(let code, let msg):
            return "Server error (\(code)): \(msg)"
        case .encodingError:
            return "Failed to encode request"
        case .decodingError(let detail):
            return "Failed to decode response: \(detail)"
        case .rateLimited(let retry):
            if let retry = retry {
                return "Rate limited. Retry in \(retry) seconds."
            }
            return "Rate limited. Please try again later."
        }
    }

    static func from(_ errorData: APIErrorData?) -> APIError {
        guard let error = errorData else {
            return .serverError(0, "Unknown error")
        }
        switch error.code {
        case "bad_request":
            if error.message.lowercased().contains("expired") {
                return .enrollmentExpired
            }
            return .invalidEnrollmentCode
        case "unauthorized":
            return .unauthorized
        case "not_found":
            return .deviceNotFound
        case "conflict":
            return .conflict(error.message)
        default:
            return .serverError(0, error.message)
        }
    }
}

// MARK: - Notification Names

extension Notification.Name {
    static let authenticationFailed = Notification.Name("authenticationFailed")
}

// MARK: - JSONValue (for passing raw JSONL events)

enum JSONValue: Codable {
    case string(String)
    case int(Int)
    case double(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let bool = try? container.decode(Bool.self) {
            self = .bool(bool)
        } else if let int = try? container.decode(Int.self) {
            self = .int(int)
        } else if let double = try? container.decode(Double.self) {
            self = .double(double)
        } else if let string = try? container.decode(String.self) {
            self = .string(string)
        } else if let array = try? container.decode([JSONValue].self) {
            self = .array(array)
        } else if let object = try? container.decode([String: JSONValue].self) {
            self = .object(object)
        } else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Invalid JSON value")
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let value):
            try container.encode(value)
        case .int(let value):
            try container.encode(value)
        case .double(let value):
            try container.encode(value)
        case .bool(let value):
            try container.encode(value)
        case .object(let value):
            try container.encode(value)
        case .array(let value):
            try container.encode(value)
        case .null:
            try container.encodeNil()
        }
    }

    init(from any: Any) {
        switch any {
        case let string as String:
            self = .string(string)
        case let int as Int:
            self = .int(int)
        case let double as Double:
            self = .double(double)
        case let bool as Bool:
            self = .bool(bool)
        case let array as [Any]:
            self = .array(array.map { JSONValue(from: $0) })
        case let dict as [String: Any]:
            self = .object(dict.mapValues { JSONValue(from: $0) })
        default:
            self = .null
        }
    }
}

// MARK: - Int Extension

extension Int {
    var nonZero: Int? {
        self == 0 ? nil : self
    }
}

// MARK: - Date Extension

extension Date {
    var relativeFormatted: String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: self, relativeTo: Date())
    }
}
