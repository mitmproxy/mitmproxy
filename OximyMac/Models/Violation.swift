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

// MARK: - Display helpers

extension ViolationEntry {
    /// Built-in Oximy/Presidio PII type keys — everything else is a custom rule name.
    private static let knownOximyTypes: Set<String> = [
        "email", "phone", "ssn", "credit_card", "api_key",
        "aws_key", "github_token", "ip_address", "private_key",
        "person_name", "location",
    ]

    /// True when detectedType is a custom regex/keyword rule name rather than a known Oximy key.
    var isCustomRule: Bool {
        let types = detectedType
            .components(separatedBy: ",")
            .map { $0.trimmingCharacters(in: .whitespaces).lowercased() }
        return !types.allSatisfy { Self.knownOximyTypes.contains($0) }
    }

    var piiIcon: String {
        let t = detectedType.lowercased()
        if t.contains("email")                          { return "envelope.fill" }
        if t.contains("credit") || t.contains("card")  { return "creditcard.fill" }
        if t.contains("ssn")                            { return "person.text.rectangle.fill" }
        if t.contains("phone")                          { return "phone.fill" }
        if t.contains("aws")                            { return "key.horizontal.fill" }
        if t.contains("github")                         { return "chevron.left.forwardslash.chevron.right" }
        if t.contains("private")                        { return "lock.fill" }
        if t.contains("ip")                             { return "network" }
        if t.contains("person") || t.contains("name")  { return "person.fill" }
        if t.contains("location")                       { return "location.fill" }
        if t.contains("key") || t.contains("token")    { return "key.fill" }
        return "text.magnifyingglass"  // custom regex/keyword rule
    }

    var piiLabel: String {
        let t = detectedType.lowercased()
        if t.contains("email")                              { return "Email Address" }
        if t.contains("credit") || t.contains("card")      { return "Credit Card" }
        if t.contains("ssn")                               { return "Social Security Number" }
        if t.contains("phone")                             { return "Phone Number" }
        if t.contains("aws")                               { return "AWS Access Key" }
        if t.contains("github")                            { return "GitHub Token" }
        if t.contains("private")                           { return "Private Key" }
        if t.contains("api_key") || t.contains("api key") { return "API Key" }
        if t.contains("ip_address") || t.contains("ip address") { return "IP Address" }
        if t.contains("person")                            { return "Person Name" }
        if t.contains("location")                          { return "Location" }
        if t.contains("token") || t.contains("key")        { return "API Key" }
        // Custom rule — the detectedType is the rule name, already human-readable
        return (detectedType.components(separatedBy: ",").first ?? detectedType)
            .trimmingCharacters(in: .whitespaces)
            .replacingOccurrences(of: "_", with: " ")
            .capitalized
    }

    /// The redaction placeholder the Python addon actually wrote into the body.
    /// Single known type → [TYPE_REDACTED]. Custom/mixed → [CUSTOM_REDACTED].
    var redactPlaceholder: String {
        let types = detectedType.components(separatedBy: ",").map {
            $0.trimmingCharacters(in: .whitespaces).lowercased()
        }
        if types.count == 1, let single = types.first,
           Self.knownOximyTypes.contains(single) {
            return "[\(single.uppercased())_REDACTED]"
        }
        return "[CUSTOM_REDACTED]"
    }

    /// Relative time string for the violation timestamp (e.g. "2 min ago").
    var relativeTime: String {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let date = iso.date(from: timestamp) ?? ISO8601DateFormatter().date(from: timestamp)
        guard let date else { return "" }
        let fmt = RelativeDateTimeFormatter()
        fmt.unitsStyle = .abbreviated
        return fmt.localizedString(for: date, relativeTo: Date())
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
