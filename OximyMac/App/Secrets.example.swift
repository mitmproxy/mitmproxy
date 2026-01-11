import Foundation

/// Secrets configuration - COPY this file to Secrets.swift and fill in your values
/// Secrets.swift is gitignored and won't be committed
enum Secrets {
    /// Sentry DSN for crash reporting
    /// Get this from: sentry.io → Settings → Projects → Client Keys (DSN)
    static let sentryDSN: String? = nil  // e.g. "https://xxx@xxx.ingest.sentry.io/xxx"
}
