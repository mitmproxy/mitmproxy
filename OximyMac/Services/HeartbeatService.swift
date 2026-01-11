import Foundation
import Darwin

@MainActor
final class HeartbeatService: ObservableObject {
    static let shared = HeartbeatService()

    @Published var lastHeartbeatTime: Date?
    @Published var isRunning = false
    @Published var lastError: String?

    private var timer: Timer?
    private var startTime: Date?

    private var intervalSeconds: Int {
        DeviceConfig.load().heartbeatIntervalSeconds
    }

    private init() {}

    func start() {
        guard !isRunning else { return }

        startTime = Date()
        isRunning = true
        lastError = nil

        SentryService.shared.addStateBreadcrumb(
            category: "heartbeat",
            message: "Heartbeat service started",
            data: ["interval": intervalSeconds]
        )

        // Send initial heartbeat
        Task { await sendHeartbeat() }

        // Schedule recurring heartbeats
        timer = Timer.scheduledTimer(withTimeInterval: TimeInterval(intervalSeconds), repeats: true) { [weak self] _ in
            Task { @MainActor in
                await self?.sendHeartbeat()
            }
        }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
        isRunning = false

        SentryService.shared.addStateBreadcrumb(
            category: "heartbeat",
            message: "Heartbeat service stopped"
        )
    }

    private func sendHeartbeat() async {
        guard APIClient.shared.isAuthenticated else { return }

        let uptimeSeconds = Int(Date().timeIntervalSince(startTime ?? Date()))

        let request = HeartbeatRequest(
            sensorVersion: Bundle.main.appVersion,
            uptimeSeconds: uptimeSeconds,
            permissions: .init(
                networkCapture: true,
                systemExtension: false,
                fullDiskAccess: false
            ),
            metrics: .init(
                cpuPercent: Self.getCPUUsage(),
                memoryMb: Self.getMemoryUsageMB(),
                eventsQueued: SyncService.shared.pendingEventCount
            )
        )

        do {
            let response = try await APIClient.shared.sendHeartbeat(request)
            lastHeartbeatTime = Date()
            lastError = nil

            SentryService.shared.addStateBreadcrumb(
                category: "heartbeat",
                message: "Heartbeat sent",
                data: ["status": response.status]
            )

            // Process any commands from the server
            if let commands = response.commands, !commands.isEmpty {
                await processCommands(commands)
            }
        } catch {
            lastError = error.localizedDescription

            SentryService.shared.addErrorBreadcrumb(
                service: "heartbeat",
                error: error.localizedDescription
            )
        }
    }

    // MARK: - System Metrics

    /// Get task basic info using Mach APIs (shared helper)
    private static func getTaskBasicInfo() -> mach_task_basic_info? {
        var info = mach_task_basic_info()
        var count = mach_msg_type_number_t(MemoryLayout<mach_task_basic_info>.size) / 4

        let result = withUnsafeMutablePointer(to: &info) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                task_info(mach_task_self_, task_flavor_t(MACH_TASK_BASIC_INFO), $0, &count)
            }
        }

        return result == KERN_SUCCESS ? info : nil
    }

    /// Get current CPU usage percentage for this process
    private static func getCPUUsage() -> Double? {
        // Verify we can get task info (also primes the system)
        guard getTaskBasicInfo() != nil else { return nil }

        // Get thread info for CPU usage
        var threadList: thread_act_array_t?
        var threadCount: mach_msg_type_number_t = 0

        let threadResult = task_threads(mach_task_self_, &threadList, &threadCount)
        guard threadResult == KERN_SUCCESS, let threads = threadList else { return nil }

        defer {
            // Always deallocate thread list
            let threadListSize = vm_size_t(Int(threadCount) * MemoryLayout<thread_t>.size)
            vm_deallocate(mach_task_self_, vm_address_t(bitPattern: threads), threadListSize)
        }

        var totalCPU: Double = 0

        for i in 0..<Int(threadCount) {
            var threadInfo = thread_basic_info()
            var threadInfoCount = mach_msg_type_number_t(THREAD_INFO_MAX)

            let infoResult = withUnsafeMutablePointer(to: &threadInfo) {
                $0.withMemoryRebound(to: integer_t.self, capacity: Int(threadInfoCount)) {
                    thread_info(threads[i], thread_flavor_t(THREAD_BASIC_INFO), $0, &threadInfoCount)
                }
            }

            if infoResult == KERN_SUCCESS && threadInfo.flags & TH_FLAGS_IDLE == 0 {
                totalCPU += Double(threadInfo.cpu_usage) / Double(TH_USAGE_SCALE) * 100.0
            }
        }

        return totalCPU
    }

    /// Get current memory usage in MB for this process
    private static func getMemoryUsageMB() -> Int? {
        guard let info = getTaskBasicInfo() else { return nil }
        // Convert from bytes to MB
        return Int(info.resident_size / (1024 * 1024))
    }

    // MARK: - Command Processing

    /// Process commands received from the server
    private func processCommands(_ commands: [String]) async {
        for command in commands {
            SentryService.shared.addStateBreadcrumb(
                category: "heartbeat",
                message: "Processing command",
                data: ["command": command]
            )

            switch command.lowercased() {
            case "sync_now":
                // Trigger immediate event sync
                await SyncService.shared.syncNow()
                print("[HeartbeatService] Executed command: sync_now")

            case "restart_proxy":
                // Restart the proxy service
                await restartProxy()
                print("[HeartbeatService] Executed command: restart_proxy")

            case "disable_proxy":
                // Disable the system proxy
                do {
                    try await ProxyService.shared.disableProxy()
                    print("[HeartbeatService] Executed command: disable_proxy")
                } catch {
                    print("[HeartbeatService] Failed to disable proxy: \(error)")
                }

            case "logout":
                // Force logout - return to enrollment
                NotificationCenter.default.post(name: .authenticationFailed, object: nil)
                print("[HeartbeatService] Executed command: logout")

            default:
                // Unknown command - log it
                print("[HeartbeatService] Unknown command received: \(command)")
                SentryService.shared.addErrorBreadcrumb(
                    service: "heartbeat",
                    error: "Unknown command: \(command)"
                )
            }
        }
    }

    /// Helper to restart the proxy
    private func restartProxy() async {
        guard let port = MITMService.shared.currentPort else { return }

        do {
            try await ProxyService.shared.disableProxy()
            try await ProxyService.shared.enableProxy(port: port)
        } catch {
            print("[HeartbeatService] Failed to restart proxy: \(error)")
            SentryService.shared.captureError(error, context: [
                "operation": "restart_proxy",
                "command_source": "heartbeat"
            ])
        }
    }
}
