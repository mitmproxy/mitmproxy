import Foundation

/// A single enforcement violation detected by the sensor
struct ViolationEntry: Codable {
    let id: String
    let timestamp: String
    let action: String  // "warn" or "block"
    let policyName: String
    let ruleName: String
    let severity: String
    let detectedType: String
    let host: String
    let bundleId: String?
    let retryAllowed: Bool
    let message: String

    enum CodingKeys: String, CodingKey {
        case id
        case timestamp
        case action
        case policyName = "policy_name"
        case ruleName = "rule_name"
        case severity
        case detectedType = "detected_type"
        case host
        case bundleId = "bundle_id"
        case retryAllowed = "retry_allowed"
        case message
    }
}

/// Envelope for the violations JSON file
struct ViolationState: Codable {
    let violations: [ViolationEntry]
    let lastUpdated: String

    enum CodingKeys: String, CodingKey {
        case violations
        case lastUpdated = "last_updated"
    }
}
