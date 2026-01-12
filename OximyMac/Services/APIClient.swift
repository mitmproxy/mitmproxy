import Foundation
import IOKit

@MainActor
final class APIClient: ObservableObject {
    static let shared = APIClient()

    @Published var isAuthenticated = false
    @Published private(set) var authFailureCount = 0

    private let session: URLSession
    private let maxAuthRetries = 5

    private var baseURL: URL {
        guard let url = URL(string: deviceConfig.apiEndpoint) else {
            // Fallback to default API endpoint if config is malformed
            return URL(string: Constants.defaultAPIEndpoint)!
        }
        return url
    }

    private var deviceToken: String? {
        UserDefaults.standard.string(forKey: Constants.Defaults.deviceToken)
    }

    private var deviceConfig: DeviceConfig {
        DeviceConfig.load()
    }

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)

        isAuthenticated = UserDefaults.standard.string(forKey: Constants.Defaults.deviceToken) != nil
    }

    // MARK: - Device Registration

    func registerDevice(enrollmentCode: String) async throws -> DeviceRegistrationResponse.DeviceData {
        var request = URLRequest(url: baseURL.appendingPathComponent("devices/register"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(enrollmentCode, forHTTPHeaderField: "X-Enrollment-Token")

        let hardwareId = Self.getHardwareUUID() ?? UUID().uuidString

        let body = DeviceRegistrationRequest(
            hostname: Host.current().localizedName ?? "Unknown",
            displayName: Host.current().localizedName,
            osVersion: ProcessInfo.processInfo.operatingSystemVersionString,
            sensorVersion: Bundle.main.appVersion,
            hardwareId: hardwareId,
            ownerEmail: nil,
            permissions: .init(
                networkCapture: true,
                systemExtension: false,
                fullDiskAccess: false
            )
        )

        request.httpBody = try JSONEncoder().encode(body)

        let response: DeviceRegistrationResponse = try await performRequest(request, authenticated: false)

        guard response.success, let data = response.data else {
            throw APIError.from(response.error)
        }

        // Store credentials
        storeCredentials(data)

        return data
    }

    // MARK: - Heartbeat

    func sendHeartbeat(_ heartbeat: HeartbeatRequest) async throws -> HeartbeatResponse.HeartbeatData {
        var request = URLRequest(url: baseURL.appendingPathComponent("devices/heartbeat"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(heartbeat)

        let response: HeartbeatResponse = try await performAuthenticatedRequest(request)

        guard response.success, let data = response.data else {
            throw APIError.from(response.error)
        }

        // Apply config updates if any
        if let configUpdate = data.configUpdate {
            configUpdate.save()
        }

        return data
    }

    // MARK: - Events

    func submitEvents(_ events: [JSONValue]) async throws -> EventBatchResponse.EventData {
        var request = URLRequest(url: baseURL.appendingPathComponent("devices/events"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = EventBatchRequest(events: events)
        request.httpBody = try JSONEncoder().encode(body)

        let response: EventBatchResponse = try await performAuthenticatedRequest(request)

        guard response.success, let data = response.data else {
            throw APIError.from(response.error)
        }

        return data
    }

    // MARK: - Request Helpers

    private func performAuthenticatedRequest<T: Decodable>(_ request: URLRequest) async throws -> T {
        guard let token = deviceToken else {
            throw APIError.unauthorized
        }

        var authedRequest = request
        authedRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        do {
            let result: T = try await performRequest(authedRequest, authenticated: true)
            authFailureCount = 0
            return result
        } catch APIError.unauthorized {
            authFailureCount += 1

            if authFailureCount >= maxAuthRetries {
                await clearCredentialsAndNotify()
                throw APIError.unauthorized
            }

            // Retry with exponential backoff
            let delay = UInt64(pow(2.0, Double(authFailureCount))) * 1_000_000_000
            try await Task.sleep(nanoseconds: delay)
            return try await performAuthenticatedRequest(request)
        }
    }

    private func performRequest<T: Decodable>(_ request: URLRequest, authenticated: Bool) async throws -> T {
        // Log request details
        print("[APIClient] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("[APIClient] REQUEST: \(request.httpMethod ?? "GET") \(request.url?.absoluteString ?? "nil")")
        print("[APIClient] Headers:")
        request.allHTTPHeaderFields?.forEach { key, value in
            if key == "Authorization" {
                // Mask the token but show prefix
                let masked = value.prefix(20) + "..." + value.suffix(4)
                print("[APIClient]   \(key): \(masked)")
            } else {
                print("[APIClient]   \(key): \(value)")
            }
        }
        if let body = request.httpBody, let bodyString = String(data: body, encoding: .utf8) {
            // Truncate if too long
            let truncated = bodyString.count > 500 ? String(bodyString.prefix(500)) + "...[truncated]" : bodyString
            print("[APIClient] Body: \(truncated)")
        }

        let (data, response): (Data, URLResponse)

        do {
            (data, response) = try await session.data(for: request)
        } catch {
            print("[APIClient] Network error: \(error.localizedDescription)")
            throw APIError.networkUnavailable
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            print("[APIClient] Invalid response type")
            throw APIError.serverError(0, "Invalid response")
        }

        // Log response details
        print("[APIClient] RESPONSE: \(httpResponse.statusCode)")
        print("[APIClient] Response Headers:")
        httpResponse.allHeaderFields.forEach { key, value in
            print("[APIClient]   \(key): \(value)")
        }
        if let responseString = String(data: data, encoding: .utf8) {
            let truncated = responseString.count > 1000 ? String(responseString.prefix(1000)) + "...[truncated]" : responseString
            print("[APIClient] Response Body: \(truncated)")
        }
        print("[APIClient] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        switch httpResponse.statusCode {
        case 200, 201:
            do {
                return try JSONDecoder().decode(T.self, from: data)
            } catch {
                throw APIError.decodingError(error.localizedDescription)
            }
        case 400:
            let apiResponse = try? JSONDecoder().decode(APIErrorResponse.self, from: data)
            if apiResponse?.error?.code == "bad_request" {
                throw APIError.invalidEnrollmentCode
            }
            throw APIError.serverError(400, apiResponse?.error?.message ?? "Bad request")
        case 401:
            throw APIError.unauthorized
        case 404:
            throw APIError.deviceNotFound
        case 409:
            let apiResponse = try? JSONDecoder().decode(APIErrorResponse.self, from: data)
            throw APIError.conflict(apiResponse?.error?.message ?? "Conflict")
        case 429:
            let retryAfter = httpResponse.value(forHTTPHeaderField: "Retry-After").flatMap(Int.init)
            throw APIError.rateLimited(retryAfter: retryAfter)
        default:
            throw APIError.serverError(httpResponse.statusCode, "Server error")
        }
    }

    // MARK: - Credentials Management

    private func storeCredentials(_ data: DeviceRegistrationResponse.DeviceData) {
        let defaults = UserDefaults.standard
        defaults.set(data.deviceToken, forKey: Constants.Defaults.deviceToken)
        defaults.set(data.deviceId, forKey: Constants.Defaults.deviceId)
        defaults.set(data.workspaceId, forKey: Constants.Defaults.workspaceId)
        defaults.set(data.workspaceName ?? data.workspaceId, forKey: Constants.Defaults.workspaceName)

        // Save config
        data.config.save()

        isAuthenticated = true
        authFailureCount = 0

        SentryService.shared.addStateBreadcrumb(
            category: "api",
            message: "Device registered",
            data: ["deviceId": data.deviceId, "workspaceId": data.workspaceId]
        )
    }

    private func clearCredentialsAndNotify() async {
        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: Constants.Defaults.deviceToken)
        defaults.removeObject(forKey: Constants.Defaults.deviceId)
        defaults.removeObject(forKey: Constants.Defaults.workspaceId)

        isAuthenticated = false

        SentryService.shared.addStateBreadcrumb(
            category: "api",
            message: "Credentials cleared due to auth failure"
        )

        NotificationCenter.default.post(name: .authenticationFailed, object: nil)
    }

    // MARK: - Hardware UUID

    static func getHardwareUUID() -> String? {
        let platformExpert = IOServiceGetMatchingService(
            kIOMainPortDefault,
            IOServiceMatching("IOPlatformExpertDevice")
        )
        guard platformExpert != 0 else { return nil }
        defer { IOObjectRelease(platformExpert) }

        guard let uuidAsCFString = IORegistryEntryCreateCFProperty(
            platformExpert,
            kIOPlatformUUIDKey as CFString,
            kCFAllocatorDefault,
            0
        )?.takeUnretainedValue() as? String else { return nil }

        return uuidAsCFString
    }
}

// MARK: - API Error Response

private struct APIErrorResponse: Decodable {
    let success: Bool
    let error: APIErrorData?
}

// MARK: - Bundle Extension

extension Bundle {
    var appVersion: String {
        infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0"
    }

    var buildNumber: String {
        infoDictionary?["CFBundleVersion"] as? String ?? "1"
    }
}
