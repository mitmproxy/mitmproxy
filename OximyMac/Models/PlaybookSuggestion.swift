import Foundation

/// A playbook definition surfaced as a proactive suggestion
struct PlaybookInfo: Codable, Identifiable {
    let id: String
    let name: String
    let description: String
    let category: String
    let promptTemplate: String
    let tags: [String]?          // Optional — server-driven suggestions don't include tags

    enum CodingKeys: String, CodingKey {
        case id, name, description, category, tags
        case promptTemplate = "prompt_template"
    }
}

/// A suggestion written by the Python addon to ~/.oximy/suggestions.json
struct PlaybookSuggestion: Codable, Identifiable {
    let id: String
    let playbook: PlaybookInfo
    let triggerExcerpt: String?  // Optional — server-driven suggestions don't include this
    let confidence: Double
    let createdAt: String
    let status: String
}
