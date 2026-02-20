import Foundation

// MARK: - Safe Bundle Module Access

/// Safe accessor for SPM's Bundle.module that doesn't crash in release builds.
/// The auto-generated Bundle.module calls fatalError if the bundle doesn't exist,
/// which happens when the binary is copied to a different app bundle (build-release.sh).
private var safeModuleBundle: Bundle? {
    // Only attempt to access Bundle.module if we're running from .build directory (SPM development)
    let executablePath = Bundle.main.executablePath ?? ""
    guard executablePath.contains(".build/") else {
        return nil
    }

    // Try to find the SPM resource bundle manually without triggering fatalError
    let mainBundlePath = Bundle.main.bundleURL.appendingPathComponent("OximyMac_OximyMac.bundle").path
    if let bundle = Bundle(path: mainBundlePath) {
        return bundle
    }

    // Try the build directory path
    let sourceDir = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().path
    let buildBundlePath = sourceDir + "/.build/arm64-apple-macosx/debug/OximyMac_OximyMac.bundle"
    if let bundle = Bundle(path: buildBundlePath) {
        return bundle
    }

    return nil
}

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

    deinit {
        // Ensure restart task is cancelled to prevent memory leaks
        restartTask?.cancel()
        restartTask = nil
    }

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

    /// Check if something is listening on a port (opposite of isPortAvailable)
    private func isPortListening(_ port: Int) -> Bool {
        let socketFD = socket(AF_INET, SOCK_STREAM, 0)
        guard socketFD >= 0 else { return false }
        defer { close(socketFD) }

        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = in_port_t(port).bigEndian
        addr.sin_addr.s_addr = inet_addr("127.0.0.1")

        let connectResult = withUnsafePointer(to: &addr) { ptr in
            ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) { sockaddrPtr in
                connect(socketFD, sockaddrPtr, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }

        return connectResult == 0
    }

    /// Wait for mitmproxy to start listening on the specified port
    /// Returns true if port becomes available within timeout, false otherwise
    private func waitForPortListening(_ port: Int, timeout: TimeInterval = 10.0) async -> Bool {
        let startTime = Date()
        let checkInterval: UInt64 = 100_000_000 // 100ms in nanoseconds

        NSLog("[MITMService] Waiting for port %d to start listening (timeout: %.1fs)...", port, timeout)

        while Date().timeIntervalSince(startTime) < timeout {
            if isPortListening(port) {
                NSLog("[MITMService] Port %d is now listening after %.2fs", port, Date().timeIntervalSince(startTime))
                return true
            }

            // Check if process has already exited
            if let proc = process, !proc.isRunning {
                NSLog("[MITMService] Process exited while waiting for port")
                return false
            }

            try? await Task.sleep(nanoseconds: checkInterval)
        }

        NSLog("[MITMService] Timeout waiting for port %d to start listening", port)
        return false
    }

    // MARK: - Process Management

    /// Kill all existing mitmproxy/mitmdump processes to ensure clean state
    /// This handles zombie processes from previous runs, crashed instances, or stale processes
    private func killAllMitmProcesses() {
        NSLog("[MITMService] Cleaning up any existing mitmproxy processes...")

        // Kill any mitmdump processes
        let killMitmdump = Process()
        killMitmdump.executableURL = URL(fileURLWithPath: "/usr/bin/pkill")
        killMitmdump.arguments = ["-9", "-f", "mitmdump"]
        killMitmdump.standardOutput = FileHandle.nullDevice
        killMitmdump.standardError = FileHandle.nullDevice
        try? killMitmdump.run()
        killMitmdump.waitUntilExit()

        // Kill any mitmproxy processes
        let killMitmproxy = Process()
        killMitmproxy.executableURL = URL(fileURLWithPath: "/usr/bin/pkill")
        killMitmproxy.arguments = ["-9", "-f", "mitmproxy"]
        killMitmproxy.standardOutput = FileHandle.nullDevice
        killMitmproxy.standardError = FileHandle.nullDevice
        try? killMitmproxy.run()
        killMitmproxy.waitUntilExit()

        // Give processes time to fully terminate
        Thread.sleep(forTimeInterval: 0.2)

        NSLog("[MITMService] Cleanup complete")
    }

    /// Start mitmproxy with the Oximy addon
    func start() async throws {
        NSLog("[MITMService]  start() called, isRunning=\(isRunning)")
        guard !isRunning else {
            NSLog("[MITMService]  Already running, returning early")
            return
        }

        // CRITICAL: Kill any existing mitmproxy processes first
        // This ensures no zombie processes from previous runs interfere
        killAllMitmProcesses()

        // Find available port
        let port = findAvailablePort()
        NSLog("[MITMService]  Found available port: \(port)")
        guard port > 0 else {
            NSLog("[MITMService]  ERROR: No available port found")
            OximyLogger.shared.log(.MITM_FAIL_301, "No available port found")
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
                "--set", "oximy_manage_proxy=true",  // Addon handles proxy based on remote sensor_enabled
                "--set", "oximy_terminal_proxy=false",  // Disable terminal proxy tracking
                "--mode", "regular@\(port)",
                "--listen-host", "127.0.0.1",
                "--ssl-insecure",
                "-q"
            ]
            // Pass app version so addon can send X-Sensor-Version header
            var fallbackEnv = ProcessInfo.processInfo.environment
            fallbackEnv["OXIMY_APP_VERSION"] = Bundle.main.appVersion
            process.environment = fallbackEnv
            self.process = process
            try runProcess(process, port: port, addonPath: addonPath)

            // CRITICAL: Wait for mitmproxy to actually start listening
            let isListening = await waitForPortListening(port)
            if !isListening {
                NSLog("[MITMService] ERROR: mitmproxy failed to start listening on port %d", port)
                stop()  // Clean up the zombie process
                throw MITMError.portNotListening(port)
            }
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

        // CRITICAL: Clear Python environment variables to prevent conflicts with local source
        // The mitmdump wrapper script will set the correct values for bundled Python
        var env = ProcessInfo.processInfo.environment
        env.removeValue(forKey: "PYTHONPATH")
        env.removeValue(forKey: "PYTHONHOME")
        env.removeValue(forKey: "PYTHONSTARTUP")
        env.removeValue(forKey: "VIRTUAL_ENV")
        // Pass app version so addon can send X-Sensor-Version header
        env["OXIMY_APP_VERSION"] = Bundle.main.appVersion
        process.environment = env

        // Run via bash wrapper script
        process.arguments = [
            mitmdumpPath,
            "-s", addonPath,
            "--set", "oximy_enabled=true",
            "--set", "oximy_output_dir=\(Constants.tracesDir.path)",
            "--set", "confdir=\(Constants.oximyDir.path)",
            "--set", "oximy_manage_proxy=true",  // Addon handles proxy based on remote sensor_enabled
            "--set", "oximy_terminal_proxy=false",  // Disable terminal proxy tracking
            "--mode", "regular@\(port)",
            "--listen-host", "127.0.0.1",
            "--ssl-insecure"
        ]

        NSLog("[MITMService] Process arguments: %@", process.arguments?.description ?? "nil")

        do {
            NSLog("[MITMService]  Calling runProcess()...")
            try runProcess(process, port: port, addonPath: addonPath)
            NSLog("[MITMService]  runProcess() completed successfully")

            // CRITICAL: Wait for mitmproxy to actually start listening
            let isListening = await waitForPortListening(port)
            if !isListening {
                NSLog("[MITMService] ERROR: mitmproxy failed to start listening on port %d", port)
                stop()  // Clean up the zombie process
                throw MITMError.portNotListening(port)
            }
            NSLog("[MITMService] mitmproxy is now listening on port %d", port)
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
        // First, terminate our tracked process if running
        if let process = process, process.isRunning {
            process.terminate()
            // Give addon time to complete final upload (typically 1-2s, max 3s)
            Thread.sleep(forTimeInterval: 3.0)
            // Force kill if still running
            if process.isRunning {
                process.interrupt()  // Send SIGINT
            }
        }

        // Then kill ALL mitmproxy processes to catch any orphans/zombies
        killAllMitmProcesses()

        self.process = nil
        self.isRunning = false
        self.currentPort = nil

        NSLog("[MITMService]  Stopped (including any zombie processes)")

        OximyLogger.shared.setTag("mitm_running", value: "false")
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

    /// Schedule an automatic restart - FAIL-OPEN: Restart immediately to minimize downtime
    /// Previous behavior used exponential backoff (2s, 4s, 8s) which left users without internet.
    /// New behavior: Restart immediately (100ms delay just for cleanup) to minimize proxy downtime.
    private func scheduleRestart() {
        guard restartAttempts < maxRestartAttempts else {
            lastError = "mitmproxy crashed too many times. Please restart Oximy."
            NSLog("[MITMService] Max restart attempts (\(self.maxRestartAttempts)) exceeded")

            OximyLogger.shared.log(.MITM_RETRY_401, "Max restart attempts exceeded", data: [
                "max_attempts": maxRestartAttempts,
                "restart_count": restartCount
            ])

            NotificationCenter.default.post(name: .mitmproxyFailed, object: nil)
            return
        }

        restartAttempts += 1
        restartCount += 1

        // FAIL-OPEN: Immediate restart with minimal delay (100ms) for cleanup
        // Previously used exponential backoff (2s, 4s, 8s) which blocked internet
        let delay: UInt64 = 100_000_000  // 100ms - just enough for process cleanup

        let maxAttempts = self.maxRestartAttempts
        NSLog("[MITMService] FAIL-OPEN: Immediate restart attempt \(self.restartAttempts)/\(maxAttempts) in 100ms")

        OximyLogger.shared.log(.MITM_RETRY_001, "Restart scheduled", data: [
            "attempt": restartAttempts,
            "max_attempts": maxRestartAttempts,
            "delay_ms": 100
        ])

        restartTask?.cancel()
        restartTask = Task {
            try? await Task.sleep(nanoseconds: delay)

            guard !Task.isCancelled else { return }

            do {
                try await start()
                // Success - reset counter
                restartAttempts = 0
                NSLog("[MITMService] FAIL-OPEN: Auto-restart successful, proxy will be re-enabled by addon")
            } catch {
                NSLog("[MITMService] FAIL-OPEN: Auto-restart failed: \(error)")
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

    // MARK: - Resource Location

    /// Locate a bundled resource using 4-priority search:
    /// 1. Bundle.main.resourcePath (release app bundle - MUST check first!)
    /// 2. Bundle.module (SPM development builds only)
    /// 3. Source-relative via #filePath (development)
    /// 4. Executable-relative (standalone binary fallback)
    ///
    /// IMPORTANT: Bundle.module must NOT be checked first because it causes a fatal error
    /// when the binary is copied to a new app bundle structure (as done by build-release.sh).
    private func locateResource(
        bundleResource: String,
        subpath: String,
        sourceFile: String = #file
    ) -> String? {
        let fm = FileManager.default

        // Priority 1: App bundle Resources (release builds via build-release.sh)
        // This MUST be checked first because Bundle.module will crash in release builds
        if let bundlePath = Bundle.main.resourcePath {
            let path = (bundlePath as NSString).appendingPathComponent("\(bundleResource)/\(subpath)")
            if fm.fileExists(atPath: path) {
                NSLog("[MITMService]  Found via app bundle: \(path)")
                return path
            }
        }

        // Priority 2: SPM development builds - use safe bundle accessor
        // IMPORTANT: Do NOT use Bundle.module directly - it calls fatalError if bundle doesn't exist
        if let moduleBundle = safeModuleBundle,
           let bundleURL = moduleBundle.url(forResource: bundleResource, withExtension: nil) {
            let path = bundleURL.appendingPathComponent(subpath).path
            if fm.fileExists(atPath: path) {
                NSLog("[MITMService]  Found via Bundle.module: \(path)")
                return path
            }
        }

        // Priority 3: Development - relative to source file
        let sourceDir = URL(fileURLWithPath: sourceFile).deletingLastPathComponent().deletingLastPathComponent().path
        let devPath = sourceDir + "/Resources/\(bundleResource)/\(subpath)"
        if fm.fileExists(atPath: devPath) {
            NSLog("[MITMService]  Found via source-relative: \(devPath)")
            return devPath
        }

        // Priority 4: Fallback to executable directory
        if let mainExecPath = Bundle.main.executablePath {
            let execDir = (mainExecPath as NSString).deletingLastPathComponent
            let fallbackPath = (execDir as NSString).appendingPathComponent("Resources/\(bundleResource)/\(subpath)")
            if fm.fileExists(atPath: fallbackPath) {
                NSLog("[MITMService]  Found via executable-relative: \(fallbackPath)")
                return fallbackPath
            }
        }

        NSLog("[MITMService]  Resource not found: \(bundleResource)/\(subpath)")
        return nil
    }

    /// Locate a bundled resource directory and return its base path
    ///
    /// IMPORTANT: Bundle.module must NOT be checked first because it causes a fatal error
    /// when the binary is copied to a new app bundle structure (as done by build-release.sh).
    private func locateResourceDirectory(
        bundleResource: String,
        verifySubpath: String,
        sourceFile: String = #file
    ) -> String? {
        let fm = FileManager.default

        // Priority 1: App bundle Resources (release builds via build-release.sh)
        // This MUST be checked first because Bundle.module will crash in release builds
        if let bundlePath = Bundle.main.resourcePath {
            let basePath = (bundlePath as NSString).appendingPathComponent(bundleResource)
            let verifyPath = (basePath as NSString).appendingPathComponent(verifySubpath)
            if fm.fileExists(atPath: verifyPath) {
                NSLog("[MITMService]  Found directory via app bundle: \(basePath)")
                return basePath
            }
        }

        // Priority 2: SPM development builds - use safe bundle accessor
        // IMPORTANT: Do NOT use Bundle.module directly - it calls fatalError if bundle doesn't exist
        if let moduleBundle = safeModuleBundle,
           let bundleURL = moduleBundle.url(forResource: bundleResource, withExtension: nil) {
            let verifyPath = bundleURL.appendingPathComponent(verifySubpath).path
            if fm.fileExists(atPath: verifyPath) {
                NSLog("[MITMService]  Found directory via Bundle.module: \(bundleURL.path)")
                return bundleURL.path
            }
        }

        // Priority 3: Development - relative to source file
        let sourceDir = URL(fileURLWithPath: sourceFile).deletingLastPathComponent().deletingLastPathComponent().path
        let devPath = sourceDir + "/Resources/\(bundleResource)"
        let devVerifyPath = devPath + "/\(verifySubpath)"
        if fm.fileExists(atPath: devVerifyPath) {
            NSLog("[MITMService]  Found directory via source-relative: \(devPath)")
            return devPath
        }

        // Priority 4: Fallback to executable directory
        if let executablePath = Bundle.main.executablePath {
            let execDir = (executablePath as NSString).deletingLastPathComponent
            let fallbackPath = (execDir as NSString).appendingPathComponent("Resources/\(bundleResource)")
            let fallbackVerifyPath = (fallbackPath as NSString).appendingPathComponent(verifySubpath)
            if fm.fileExists(atPath: fallbackVerifyPath) {
                NSLog("[MITMService]  Found directory via executable-relative: \(fallbackPath)")
                return fallbackPath
            }
        }

        NSLog("[MITMService]  Resource directory not found: \(bundleResource)")
        return nil
    }

    private func getAddonPath() -> String {
        locateResource(bundleResource: "oximy-addon", subpath: "addon.py") ?? ""
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
        // Use shared locator to find python-embed directory
        guard let pythonHome = locateResourceDirectory(
            bundleResource: "python-embed",
            verifySubpath: "bin/python3"
        ) else {
            return nil
        }
        let pythonPath = (pythonHome as NSString).appendingPathComponent("bin/python3")
        return BundledPythonInfo(pythonPath: pythonPath, pythonHome: pythonHome)
    }

    /// Get path to bundled mitmdump (inside python-embed)
    /// The mitmdump script is a bash wrapper that sets up PYTHONHOME/PYTHONPATH
    /// to make the bundled Python fully self-contained and relocatable
    private func getBundledMitmdumpPath() -> String? {
        locateResource(bundleResource: "python-embed", subpath: "bin/mitmdump")
    }

    /// Run the process with all the setup (extracted to avoid duplication)
    private func runProcess(_ process: Process, port: Int, addonPath: String) throws {
        NSLog("[MITMService] runProcess() - Setting up process...")

        // Redirect stdin to /dev/null
        process.standardInput = FileHandle.nullDevice

        // Create log file for mitmproxy output
        let logFilePath = Constants.logsDir.appendingPathComponent("mitmdump.log")

        // Rotate log if it exists and is too large (> 10MB)
        let fm = FileManager.default
        if fm.fileExists(atPath: logFilePath.path),
           let attrs = try? fm.attributesOfItem(atPath: logFilePath.path),
           let size = attrs[.size] as? Int64,
           size > 10_000_000 {
            let rotatedPath = Constants.logsDir.appendingPathComponent("mitmdump.log.old")
            try? fm.removeItem(at: rotatedPath)
            try? fm.moveItem(at: logFilePath, to: rotatedPath)
        }

        // Create or append to log file
        if !fm.fileExists(atPath: logFilePath.path) {
            fm.createFile(atPath: logFilePath.path, contents: nil, attributes: nil)
        }

        let logFileHandle: FileHandle?
        do {
            logFileHandle = try FileHandle(forWritingTo: logFilePath)
            logFileHandle?.seekToEndOfFile()

            // Write startup marker
            let startupMarker = "\n\n========== MITM STARTED at \(Date()) ==========\n"
            if let data = startupMarker.data(using: .utf8) {
                logFileHandle?.write(data)
            }
        } catch {
            NSLog("[MITMService] WARNING: Could not open log file: \(error)")
            logFileHandle = nil
        }

        // Capture both stdout and stderr
        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe

        // Read stdout in background and write to both NSLog and file
        stdoutPipe.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty {
                if let str = String(data: data, encoding: .utf8) {
                    NSLog("[MITMService] STDOUT: %@", str)
                }
                logFileHandle?.write(data)
            }
        }

        // Read stderr in background and write to both NSLog and file
        stderrPipe.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty {
                if let str = String(data: data, encoding: .utf8) {
                    NSLog("[MITMService] STDERR: %@", str)
                }
                logFileHandle?.write(data)
            }
        }

        // Handle process termination with auto-restart
        process.terminationHandler = { [weak self] proc in
            Task { @MainActor [weak self] in
                guard let self = self else { return }

                self.isRunning = false
                self.currentPort = nil

                // Check termination reason
                let status = proc.terminationStatus
                let isNormalExit = status == 0 || status == 15  // 0 = success, 15 = SIGTERM

                // CRITICAL: Always disable proxy when mitmproxy stops to prevent internet blackhole
                // This handles both normal exits and crashes
                NSLog("[MITMService] Process terminated, disabling proxy to prevent internet loss")
                ProxyService.shared.disableProxySync()

                if !isNormalExit {
                    self.lastError = "mitmproxy crashed (exit code \(status))"
                    NSLog("[MITMService] Process crashed with exit code %d", status)

                    // Map exit code to signal name
                    let signalName: String
                    let interpretation: String
                    switch Int(status) {
                    case 9, 137: signalName = "SIGKILL"; interpretation = "oom_or_force_kill"
                    case 11, 139: signalName = "SIGSEGV"; interpretation = "memory_corruption"
                    case 15, 143: signalName = "SIGTERM"; interpretation = "normal_termination"
                    case 6, 134: signalName = "SIGABRT"; interpretation = "abort"
                    default: signalName = "SIG\(status)"; interpretation = "unknown"
                    }

                    OximyLogger.shared.log(.MITM_FAIL_306, "mitmproxy process crashed", data: [
                        "exit_code": status,
                        "signal_name": signalName,
                        "interpretation": interpretation,
                        "restart_attempt": self.restartAttempts,
                        "pid": proc.processIdentifier
                    ], err: (type: "MITMError", code: "MITM_CRASH", message: "Process exited with code \(status)"))

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

        OximyLogger.shared.log(.MITM_START_002, "mitmproxy listening", data: [
            "port": port,
            "pid": process.processIdentifier
        ])
        OximyLogger.shared.setTag("mitm_running", value: "true")
        OximyLogger.shared.setTag("mitm_port", value: String(port))
    }
}

// MARK: - Errors

enum MITMError: LocalizedError {
    case noAvailablePort
    case addonNotFound(String)
    case mitmdumpNotFound
    case processStartFailed(String)
    case portNotListening(Int)

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
        case .portNotListening(let port):
            return "mitmproxy failed to start listening on port \(port)"
        }
    }
}
