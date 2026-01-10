import Foundation

/// Service to manage the mitmproxy process
@MainActor
class MITMService: ObservableObject {
    static let shared = MITMService()

    @Published var isRunning = false
    @Published var currentPort: Int?
    @Published var lastError: String?
    @Published var restartCount: Int = 0

    private var process: Process?
    private var outputPipe: Pipe?
    private var errorPipe: Pipe?

    // Auto-restart configuration
    private var autoRestartEnabled = true
    private var restartAttempts = 0
    private let maxRestartAttempts = 3
    private var restartTask: Task<Void, Never>?

    private init() {}

    // MARK: - Port Selection

    /// Find an available port starting from preferred port
    func findAvailablePort() -> Int {
        // Try preferred port first
        if isPortAvailable(Constants.preferredPort) {
            return Constants.preferredPort
        }

        // Try ports above (1031-1130)
        for offset in 1...100 {
            let port = Constants.preferredPort + offset
            if isPortAvailable(port) {
                return port
            }
        }

        // Try ports below (1029-930)
        for offset in 1...100 {
            let port = Constants.preferredPort - offset
            if port > 0 && isPortAvailable(port) {
                return port
            }
        }

        // Fallback to any available port (let OS assign)
        return 0
    }

    private func isPortAvailable(_ port: Int) -> Bool {
        let socketFD = socket(AF_INET, SOCK_STREAM, 0)
        guard socketFD >= 0 else { return false }
        defer { close(socketFD) }

        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = in_port_t(port).bigEndian
        addr.sin_addr.s_addr = inet_addr("127.0.0.1")

        let bindResult = withUnsafePointer(to: &addr) { ptr in
            ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) { sockaddrPtr in
                bind(socketFD, sockaddrPtr, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }

        return bindResult == 0
    }

    // MARK: - Process Management

    /// Start mitmproxy with the Oximy addon
    func start() async throws {
        guard !isRunning else { return }

        // Find available port
        let port = findAvailablePort()
        guard port > 0 else {
            throw MITMError.noAvailablePort
        }

        // Ensure oximy directory exists
        try ensureOximyDirectoryExists()

        // Get path to the addon
        let addonPath = getAddonPath()
        guard FileManager.default.fileExists(atPath: addonPath) else {
            throw MITMError.addonNotFound(addonPath)
        }

        // Build mitmdump command
        // For now, use system Python/mitmdump. Later we'll bundle our own.
        let mitmdumpPath = findMitmdump()
        guard let mitmdumpPath = mitmdumpPath else {
            throw MITMError.mitmdumpNotFound
        }

        let process = Process()
        process.executableURL = URL(fileURLWithPath: mitmdumpPath)
        process.arguments = [
            "-s", addonPath,
            "--set", "oximy_enabled=true",
            "--set", "oximy_output_dir=\(Constants.tracesDir.path)",
            "--set", "confdir=\(Constants.oximyDir.path)",
            "--mode", "regular@\(port)",
            "--listen-host", "127.0.0.1",
            "--ssl-insecure",  // Don't verify upstream certs (we're a proxy)
            "-q"  // Quiet mode
        ]

        // Capture output
        let outputPipe = Pipe()
        let errorPipe = Pipe()
        process.standardOutput = outputPipe
        process.standardError = errorPipe

        // Handle process termination with auto-restart
        process.terminationHandler = { [weak self] proc in
            Task { @MainActor in
                guard let self = self else { return }

                self.isRunning = false
                self.currentPort = nil

                // Check termination reason
                let status = proc.terminationStatus
                let isNormalExit = status == 0 || status == 15  // 0 = success, 15 = SIGTERM

                if !isNormalExit {
                    self.lastError = "mitmproxy crashed (exit code \(status))"
                    print("[MITMService] Process crashed with exit code \(status)")

                    // Attempt auto-restart if enabled
                    if self.autoRestartEnabled {
                        self.scheduleRestart()
                    }
                }
            }
        }

        do {
            try process.run()
            self.process = process
            self.outputPipe = outputPipe
            self.errorPipe = errorPipe
            self.isRunning = true
            self.currentPort = port
            self.lastError = nil

            // Start reading output in background
            Task.detached { [weak self] in
                await self?.readOutput(from: errorPipe)
            }

            print("[MITMService] Started on port \(port)")
        } catch {
            throw MITMError.processStartFailed(error.localizedDescription)
        }
    }

    /// Stop the mitmproxy process
    func stop() {
        guard let process = process, process.isRunning else { return }

        process.terminate()
        self.process = nil
        self.isRunning = false
        self.currentPort = nil

        print("[MITMService] Stopped")
    }

    /// Restart the mitmproxy process
    func restart() async throws {
        stop()
        try await Task.sleep(nanoseconds: 500_000_000) // 0.5 second
        try await start()
    }

    // MARK: - Auto-Restart

    /// Schedule an automatic restart with exponential backoff
    private func scheduleRestart() {
        guard restartAttempts < maxRestartAttempts else {
            lastError = "mitmproxy crashed too many times. Please restart Oximy."
            print("[MITMService] Max restart attempts (\(maxRestartAttempts)) exceeded")
            NotificationCenter.default.post(name: .mitmproxyFailed, object: nil)
            return
        }

        restartAttempts += 1
        restartCount += 1

        // Exponential backoff: 2s, 4s, 8s
        let delay = UInt64(pow(2.0, Double(restartAttempts))) * 1_000_000_000

        print("[MITMService] Scheduling restart attempt \(restartAttempts)/\(maxRestartAttempts) in \(delay / 1_000_000_000)s")

        restartTask?.cancel()
        restartTask = Task {
            try? await Task.sleep(nanoseconds: delay)

            guard !Task.isCancelled else { return }

            do {
                try await start()
                // Success - reset counter
                restartAttempts = 0
                print("[MITMService] Auto-restart successful")
            } catch {
                print("[MITMService] Auto-restart failed: \(error)")
                // Will trigger another restart attempt via termination handler
            }
        }
    }

    /// Reset restart counter (call after manual intervention)
    func resetRestartCounter() {
        restartAttempts = 0
        restartCount = 0
        lastError = nil
    }

    /// Enable or disable auto-restart
    func setAutoRestart(enabled: Bool) {
        autoRestartEnabled = enabled
        if !enabled {
            restartTask?.cancel()
        }
    }

    // MARK: - Helpers

    private func ensureOximyDirectoryExists() throws {
        let fm = FileManager.default

        // Create ~/.oximy/
        if !fm.fileExists(atPath: Constants.oximyDir.path) {
            try fm.createDirectory(at: Constants.oximyDir, withIntermediateDirectories: true)
        }

        // Create ~/.oximy/traces/
        if !fm.fileExists(atPath: Constants.tracesDir.path) {
            try fm.createDirectory(at: Constants.tracesDir, withIntermediateDirectories: true)
        }

        // Create ~/.oximy/logs/
        if !fm.fileExists(atPath: Constants.logsDir.path) {
            try fm.createDirectory(at: Constants.logsDir, withIntermediateDirectories: true)
        }
    }

    private func getAddonPath() -> String {
        // First, check if addon is bundled with app (copied via .copy in Package.swift)
        if let bundleURL = Bundle.module.url(forResource: "oximy-addon", withExtension: nil) {
            let addonPath = bundleURL.appendingPathComponent("addon.py").path
            if FileManager.default.fileExists(atPath: addonPath) {
                print("[MITMService] Using bundled addon: \(addonPath)")
                return addonPath
            }
        }

        // Development fallback: check Resources directory directly
        let devResourcesPath = "/Users/namanambavi/Desktop/Oximy/Code/mitmproxy/OximyMac/Resources/oximy-addon/addon.py"
        if FileManager.default.fileExists(atPath: devResourcesPath) {
            print("[MITMService] Using dev resources addon: \(devResourcesPath)")
            return devResourcesPath
        }

        // Development fallback: use the addon in the mitmproxy repo
        let devPath = "/Users/namanambavi/Desktop/Oximy/Code/mitmproxy/mitmproxy/addons/oximy/addon.py"
        if FileManager.default.fileExists(atPath: devPath) {
            print("[MITMService] Using mitmproxy repo addon: \(devPath)")
            return devPath
        }

        // Alternative path
        let altPath = "/Users/namanambavi/Desktop/Oximy/Code/mitmproxy/addons/oximy/addon.py"
        print("[MITMService] Fallback addon path: \(altPath)")
        return altPath
    }

    /// Find mitmdump - prefer bundled, fallback to system
    private func findMitmdump() -> String? {
        // 1. Check for bundled Python with mitmproxy (production)
        if let bundledPath = getBundledMitmdumpPath() {
            print("[MITMService] Using bundled mitmdump: \(bundledPath)")
            return bundledPath
        }

        // 2. Development fallback: system mitmproxy
        let systemPaths = [
            "/opt/homebrew/bin/mitmdump",      // Homebrew on Apple Silicon
            "/usr/local/bin/mitmdump",          // Homebrew on Intel
            "/usr/bin/mitmdump",                // System
            "\(NSHomeDirectory())/.local/bin/mitmdump",  // pipx
        ]

        for path in systemPaths {
            if FileManager.default.fileExists(atPath: path) {
                print("[MITMService] Using system mitmdump: \(path)")
                return path
            }
        }

        // 3. Try to find via `which`
        let whichProcess = Process()
        whichProcess.executableURL = URL(fileURLWithPath: "/usr/bin/which")
        whichProcess.arguments = ["mitmdump"]

        let pipe = Pipe()
        whichProcess.standardOutput = pipe

        do {
            try whichProcess.run()
            whichProcess.waitUntilExit()

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let path = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
               !path.isEmpty {
                print("[MITMService] Found mitmdump via which: \(path)")
                return path
            }
        } catch {
            print("[MITMService] Could not find mitmdump via which: \(error)")
        }

        return nil
    }

    /// Get path to bundled mitmdump (inside python-embed)
    private func getBundledMitmdumpPath() -> String? {
        // Check Bundle.module for SPM builds (copied via .copy in Package.swift)
        if let pythonEmbedURL = Bundle.module.url(forResource: "python-embed", withExtension: nil) {
            let mitmdumpPath = pythonEmbedURL.appendingPathComponent("bin/mitmdump").path
            if FileManager.default.fileExists(atPath: mitmdumpPath) {
                return mitmdumpPath
            }
        }

        // Development: check Resources directory directly
        let devPath = "/Users/namanambavi/Desktop/Oximy/Code/mitmproxy/OximyMac/Resources/python-embed/bin/mitmdump"
        if FileManager.default.fileExists(atPath: devPath) {
            return devPath
        }

        return nil
    }

    private func readOutput(from pipe: Pipe) async {
        let handle = pipe.fileHandleForReading

        while true {
            let data = handle.availableData
            if data.isEmpty { break }

            if let output = String(data: data, encoding: .utf8) {
                print("[mitmproxy] \(output)")
            }
        }
    }
}

// MARK: - Errors

enum MITMError: LocalizedError {
    case noAvailablePort
    case addonNotFound(String)
    case mitmdumpNotFound
    case processStartFailed(String)

    var errorDescription: String? {
        switch self {
        case .noAvailablePort:
            return "No available port found for mitmproxy"
        case .addonNotFound(let path):
            return "Oximy addon not found at: \(path)"
        case .mitmdumpNotFound:
            return "mitmdump not found. Please install mitmproxy."
        case .processStartFailed(let reason):
            return "Failed to start mitmproxy: \(reason)"
        }
    }
}
