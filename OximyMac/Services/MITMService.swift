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

        // Enable SO_REUSEADDR to allow binding to a port in TIME_WAIT state
        // This is important for quick restart - without it, the port stays
        // "unavailable" for ~30-60 seconds after mitmproxy stops
        var reuseAddr: Int32 = 1
        setsockopt(socketFD, SOL_SOCKET, SO_REUSEADDR, &reuseAddr, socklen_t(MemoryLayout<Int32>.size))

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
        NSLog("[MITMService]  start() called, isRunning=\(isRunning)")
        guard !isRunning else {
            NSLog("[MITMService]  Already running, returning early")
            return
        }

        // Find available port
        let port = findAvailablePort()
        NSLog("[MITMService]  Found available port: \(port)")
        guard port > 0 else {
            NSLog("[MITMService]  ERROR: No available port found")
            throw MITMError.noAvailablePort
        }

        // Ensure oximy directory exists
        try ensureOximyDirectoryExists()
        NSLog("[MITMService]  Oximy directories ensured")

        // Get path to the addon
        let addonPath = getAddonPath()
        NSLog("[MITMService]  Addon path: \(addonPath)")
        guard FileManager.default.fileExists(atPath: addonPath) else {
            NSLog("[MITMService]  ERROR: Addon not found at \(addonPath)")
            throw MITMError.addonNotFound(addonPath)
        }
        NSLog("[MITMService]  Addon file exists: YES")

        // Find bundled Python and set up environment
        NSLog("[MITMService]  Looking for bundled Python...")
        guard let pythonInfo = getBundledPythonInfo() else {
            NSLog("[MITMService]  Bundled Python NOT found, falling back to system mitmdump")
            // Fallback to system mitmdump if bundled Python not available
            guard let mitmdumpPath = findMitmdump() else {
                NSLog("[MITMService]  ERROR: System mitmdump also not found")
                throw MITMError.mitmdumpNotFound
            }

            NSLog("[MITMService]  Using system mitmdump: \(mitmdumpPath)")
            let process = Process()
            process.executableURL = URL(fileURLWithPath: mitmdumpPath)
            process.arguments = [
                "-s", addonPath,
                "--set", "oximy_enabled=true",
                "--set", "oximy_output_dir=\(Constants.tracesDir.path)",
                "--set", "confdir=\(Constants.oximyDir.path)",
                "--mode", "regular@\(port)",
                "--listen-host", "127.0.0.1",
                "--ssl-insecure",
                "-q"
            ]
            self.process = process
            try runProcess(process, port: port, addonPath: addonPath)
            return
        }

        NSLog("[MITMService] Found bundled Python home: %@", pythonInfo.pythonHome)

        // Use the mitmdump wrapper script which handles environment setup properly
        let mitmdumpPath = pythonInfo.pythonHome + "/bin/mitmdump"
        guard FileManager.default.fileExists(atPath: mitmdumpPath) else {
            NSLog("[MITMService] ERROR: mitmdump script not found at %@", mitmdumpPath)
            throw MITMError.mitmdumpNotFound
        }
        NSLog("[MITMService] Using mitmdump wrapper: %@", mitmdumpPath)

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/bash")

        // CRITICAL: Set working directory to home to avoid local mitmproxy source
        process.currentDirectoryURL = FileManager.default.homeDirectoryForCurrentUser

        // Run via bash wrapper script
        process.arguments = [
            mitmdumpPath,
            "-s", addonPath,
            "--set", "oximy_enabled=true",
            "--set", "oximy_output_dir=\(Constants.tracesDir.path)",
            "--set", "confdir=\(Constants.oximyDir.path)",
            "--mode", "regular@\(port)",
            "--listen-host", "127.0.0.1",
            "--ssl-insecure",
            "-q"
        ]

        NSLog("[MITMService] Process arguments: %@", process.arguments?.description ?? "nil")

        do {
            NSLog("[MITMService]  Calling runProcess()...")
            try runProcess(process, port: port, addonPath: addonPath)
            NSLog("[MITMService]  runProcess() completed successfully")
        } catch {
            NSLog("[MITMService]  ERROR: runProcess() failed: \(error)")
            let mitmError = MITMError.processStartFailed(error.localizedDescription)
            SentryService.shared.captureError(mitmError, context: [
                "operation": "mitm_start",
                "port_attempted": port,
                "addon_path": addonPath
            ])
            throw mitmError
        }
    }

    /// Stop the mitmproxy process
    func stop() {
        guard let process = process, process.isRunning else { return }

        process.terminate()
        self.process = nil
        self.isRunning = false
        self.currentPort = nil

        NSLog("[MITMService]  Stopped")

        SentryService.shared.addStateBreadcrumb(
            category: "mitm",
            message: "Process stopped"
        )
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
            NSLog("[MITMService] Max restart attempts (\(self.maxRestartAttempts)) exceeded")

            // Capture critical error to Sentry
            SentryService.shared.captureMessage(
                "mitmproxy exceeded max restart attempts (\(maxRestartAttempts))",
                level: .error
            )

            NotificationCenter.default.post(name: .mitmproxyFailed, object: nil)
            return
        }

        restartAttempts += 1
        restartCount += 1

        // Exponential backoff: 2s, 4s, 8s
        let delay = UInt64(pow(2.0, Double(restartAttempts))) * 1_000_000_000

        let maxAttempts = self.maxRestartAttempts
        NSLog("[MITMService] Scheduling restart attempt \(self.restartAttempts)/\(maxAttempts) in \(delay / 1_000_000_000)s")

        // Add breadcrumb for restart attempt
        SentryService.shared.addStateBreadcrumb(
            category: "mitm",
            message: "Restart scheduled",
            data: [
                "attempt": restartAttempts,
                "max_attempts": maxRestartAttempts,
                "delay_seconds": delay / 1_000_000_000
            ]
        )

        restartTask?.cancel()
        restartTask = Task {
            try? await Task.sleep(nanoseconds: delay)

            guard !Task.isCancelled else { return }

            do {
                try await start()
                // Success - reset counter
                restartAttempts = 0
                NSLog("[MITMService]  Auto-restart successful")
            } catch {
                NSLog("[MITMService]  Auto-restart failed: \(error)")
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
        // First, check if addon is bundled with app (copied via build scripts)
        if let bundleURL = Bundle.module.url(forResource: "oximy-addon", withExtension: nil) {
            let addonPath = bundleURL.appendingPathComponent("addon.py").path
            if FileManager.default.fileExists(atPath: addonPath) {
                NSLog("[MITMService]  Using bundled addon: \(addonPath)")
                return addonPath
            }
        }

        // Check inside the app bundle (for release builds)
        if let bundlePath = Bundle.main.resourcePath {
            let addonPath = (bundlePath as NSString).appendingPathComponent("oximy-addon/addon.py")
            if FileManager.default.fileExists(atPath: addonPath) {
                NSLog("[MITMService]  Using app bundle addon: \(addonPath)")
                return addonPath
            }
        }

        // Development: use the standalone addon in Resources (has absolute imports)
        // This addon is a copy from mitmproxy source with imports modified to work standalone
        let devPath = "/Users/namanambavi/Desktop/Oximy/Code/mitmproxy/OximyMac/Resources/oximy-addon/addon.py"
        if FileManager.default.fileExists(atPath: devPath) {
            NSLog("[MITMService]  Using Resources addon: \(devPath)")
            return devPath
        }

        NSLog("[MITMService]  WARNING: Addon not found")
        return devPath
    }

    /// Find mitmdump - prefer bundled, fallback to system
    private func findMitmdump() -> String? {
        // 1. Check for bundled Python with mitmproxy (production)
        if let bundledPath = getBundledMitmdumpPath() {
            NSLog("[MITMService]  Using bundled mitmdump: \(bundledPath)")
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
                NSLog("[MITMService]  Using system mitmdump: \(path)")
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
                NSLog("[MITMService]  Found mitmdump via which: \(path)")
                return path
            }
        } catch {
            NSLog("[MITMService]  Could not find mitmdump via which: \(error)")
        }

        return nil
    }

    /// Information about the bundled Python installation
    private struct BundledPythonInfo {
        let pythonPath: String
        let pythonHome: String
    }

    /// Get bundled Python path and home directory
    private func getBundledPythonInfo() -> BundledPythonInfo? {
        // Check Bundle.module for SPM builds
        if let pythonEmbedURL = Bundle.module.url(forResource: "python-embed", withExtension: nil) {
            let pythonPath = pythonEmbedURL.appendingPathComponent("bin/python3").path
            if FileManager.default.fileExists(atPath: pythonPath) {
                return BundledPythonInfo(pythonPath: pythonPath, pythonHome: pythonEmbedURL.path)
            }
        }

        // Check inside the app bundle (for release builds)
        if let bundlePath = Bundle.main.resourcePath {
            let pythonHome = (bundlePath as NSString).appendingPathComponent("python-embed")
            let pythonPath = (pythonHome as NSString).appendingPathComponent("bin/python3")
            if FileManager.default.fileExists(atPath: pythonPath) {
                return BundledPythonInfo(pythonPath: pythonPath, pythonHome: pythonHome)
            }
        }

        // Development: check Resources directory directly
        let devPythonHome = "/Users/namanambavi/Desktop/Oximy/Code/mitmproxy/OximyMac/Resources/python-embed"
        let devPythonPath = devPythonHome + "/bin/python3"
        if FileManager.default.fileExists(atPath: devPythonPath) {
            return BundledPythonInfo(pythonPath: devPythonPath, pythonHome: devPythonHome)
        }

        return nil
    }

    /// Get path to bundled mitmdump (inside python-embed)
    /// The mitmdump script is a bash wrapper that sets up PYTHONHOME/PYTHONPATH
    /// to make the bundled Python fully self-contained and relocatable
    private func getBundledMitmdumpPath() -> String? {
        // Check Bundle.module for SPM builds (copied via build scripts)
        if let pythonEmbedURL = Bundle.module.url(forResource: "python-embed", withExtension: nil) {
            let mitmdumpPath = pythonEmbedURL.appendingPathComponent("bin/mitmdump").path
            if FileManager.default.fileExists(atPath: mitmdumpPath) {
                return mitmdumpPath
            }
        }

        // Check inside the app bundle (for release builds)
        if let bundlePath = Bundle.main.resourcePath {
            let mitmdumpPath = (bundlePath as NSString).appendingPathComponent("python-embed/bin/mitmdump")
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

    /// Run the process with all the setup (extracted to avoid duplication)
    private func runProcess(_ process: Process, port: Int, addonPath: String) throws {
        NSLog("[MITMService] runProcess() - Setting up process...")

        // Don't capture output - let it go to /dev/null to avoid pipe issues
        // The process was exiting because pipes were being closed
        process.standardOutput = FileHandle.nullDevice
        process.standardError = FileHandle.nullDevice

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
                    NSLog("[MITMService] Process crashed with exit code %d", status)

                    SentryService.shared.addErrorBreadcrumb(
                        service: "mitm",
                        error: "Process crashed with exit code \(status)"
                    )

                    if self.autoRestartEnabled {
                        self.scheduleRestart()
                    }
                } else {
                    NSLog("[MITMService] Process exited normally with code %d", status)
                }
            }
        }

        NSLog("[MITMService]  runProcess() - Calling process.run()...")
        try process.run()
        NSLog("[MITMService]  runProcess() - process.run() succeeded, PID: \(process.processIdentifier)")

        self.process = process
        self.isRunning = true
        self.currentPort = port
        self.lastError = nil

        NSLog("[MITMService] Started on port %d, PID: %d", port, process.processIdentifier)

        SentryService.shared.addStateBreadcrumb(
            category: "mitm",
            message: "Process started",
            data: ["port": port]
        )
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
