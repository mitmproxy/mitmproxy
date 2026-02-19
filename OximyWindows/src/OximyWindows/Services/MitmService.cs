using System.Collections.Concurrent;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using OximyWindows.Core;

namespace OximyWindows.Services;

/// <summary>
/// Manages the mitmproxy subprocess lifecycle.
/// Handles port finding, process spawning, FAIL-OPEN crash recovery with immediate restart.
/// </summary>
public class MitmService : IDisposable
{
    private Process? _mitmProcess;
    private IntPtr _jobHandle = IntPtr.Zero;
    private CancellationTokenSource? _restartCts;
    private int _restartAttempts;
    private bool _disposed;
    private bool _intentionalStop;

    public int? CurrentPort { get; private set; }
    public bool IsRunning => _mitmProcess is { HasExited: false };

    public event EventHandler? Started;
    public event EventHandler? Stopped;
    public event EventHandler? MaxRestartsExceeded;
    public event EventHandler<string>? OutputReceived;
    public event EventHandler<string>? ErrorReceived;

    /// <summary>
    /// Kill all existing mitmdump/mitmproxy processes to ensure clean state.
    /// Handles zombie processes from previous runs, crashed instances, or stale processes.
    /// </summary>
    private static void KillAllMitmProcesses()
    {
        Debug.WriteLine("[MitmService] Cleaning up any existing mitmproxy processes...");

        foreach (var name in new[] { "mitmdump", "mitmproxy" })
        {
            try
            {
                foreach (var proc in Process.GetProcessesByName(name))
                {
                    try
                    {
                        proc.Kill(entireProcessTree: true);
                        Debug.WriteLine($"[MitmService] Killed {name} process (PID {proc.Id})");
                    }
                    catch (Exception ex)
                    {
                        Debug.WriteLine($"[MitmService] Failed to kill {name} PID {proc.Id}: {ex.Message}");
                    }
                    finally
                    {
                        proc.Dispose();
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[MitmService] Error enumerating {name} processes: {ex.Message}");
            }
        }

        // Give processes time to fully terminate
        Thread.Sleep(200);
        Debug.WriteLine("[MitmService] Cleanup complete");
    }

    /// <summary>
    /// Kill any process listening on the specified port.
    /// Catches zombie python.exe or other processes that KillAllMitmProcesses misses
    /// because they don't have "mitmdump" in their process name.
    /// </summary>
    private static void KillProcessOnPort(int port)
    {
        try
        {
            var startInfo = new ProcessStartInfo
            {
                FileName = "netstat",
                Arguments = "-ano",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                CreateNoWindow = true
            };

            using var process = Process.Start(startInfo);
            if (process == null) return;

            var output = process.StandardOutput.ReadToEnd();
            process.WaitForExit(5000);

            foreach (var line in output.Split('\n'))
            {
                if (line.Contains($":{port}") && line.Contains("LISTENING"))
                {
                    var parts = line.Split(Array.Empty<char>(), StringSplitOptions.RemoveEmptyEntries);
                    if (parts.Length >= 5 && int.TryParse(parts[^1].Trim(), out var pid))
                    {
                        // Don't kill ourselves
                        if (pid == Environment.ProcessId) continue;

                        try
                        {
                            using var proc = Process.GetProcessById(pid);
                            Debug.WriteLine($"[MitmService] Killing {proc.ProcessName} (PID {pid}) holding port {port}");
                            proc.Kill(entireProcessTree: true);
                        }
                        catch (Exception ex)
                        {
                            Debug.WriteLine($"[MitmService] Failed to kill PID {pid} on port {port}: {ex.Message}");
                        }
                    }
                }
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[MitmService] Port cleanup check failed: {ex.Message}");
        }
    }

    /// <summary>
    /// Rotate mitmdump.log if it exceeds 10MB.
    /// </summary>
    private static void RotateLogIfNeeded()
    {
        try
        {
            var logPath = Path.Combine(Constants.LogsDir, "mitmdump.log");
            if (!File.Exists(logPath)) return;

            var fileInfo = new FileInfo(logPath);
            if (fileInfo.Length <= 10_000_000) return; // 10MB threshold

            var rotatedPath = Path.Combine(Constants.LogsDir, "mitmdump.log.old");

            if (File.Exists(rotatedPath))
                File.Delete(rotatedPath);

            File.Move(logPath, rotatedPath);
            Debug.WriteLine($"[MitmService] Rotated mitmdump.log ({fileInfo.Length / 1_000_000}MB) to mitmdump.log.old");
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[MitmService] Log rotation failed: {ex.Message}");
        }
    }

    /// <summary>
    /// Start the mitmproxy process.
    /// </summary>
    public async Task StartAsync()
    {
        if (IsRunning)
            return;

        // CRITICAL: Kill any existing mitmproxy processes first
        // This ensures no zombie processes from previous runs interfere
        KillAllMitmProcesses();

        // Also kill anything holding our preferred port (catches zombie python.exe etc.)
        KillProcessOnPort(Constants.PreferredPort);
        Thread.Sleep(300); // Give port time to be released

        // Rotate log file if too large
        RotateLogIfNeeded();

        var port = FindAvailablePort();
        if (port == 0)
        {
            OximyLogger.Log(EventCode.MITM_FAIL_301, "No available port found");
            throw new MitmException("No available port found in range");
        }

        // Ensure mitmproxy directory exists - mitmproxy will auto-generate CA certificate
        Directory.CreateDirectory(Constants.MitmproxyDir);

        // Ensure mitmdump exists
        if (!File.Exists(Constants.MitmdumpExePath))
            throw new MitmException($"mitmdump not found at {Constants.MitmdumpExePath}. Please ensure Python is bundled correctly.");

        var startInfo = new ProcessStartInfo
        {
            FileName = Constants.MitmdumpExePath,
            Arguments = BuildArguments(port),
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            WorkingDirectory = Constants.PythonEmbedDir
        };

        // Set environment for embedded Python - critical for Windows embeddable package
        var sitePackages = Path.Combine(Constants.PythonEmbedDir, "Lib", "site-packages");
        startInfo.Environment["PYTHONHOME"] = Constants.PythonEmbedDir;
        startInfo.Environment["PYTHONPATH"] = $"{sitePackages};{Constants.AddonDir}";
        startInfo.Environment["PYTHONNOUSERSITE"] = "1";
        startInfo.Environment["PYTHONDONTWRITEBYTECODE"] = "1";
        startInfo.Environment["PYTHONUTF8"] = "1";

        // Pass Sentry DSN and session ID to Python addon for cross-component correlation
        var sentryDsn = Environment.GetEnvironmentVariable("SENTRY_DSN") ?? Secrets.SentryDsn;
        if (!string.IsNullOrEmpty(sentryDsn))
            startInfo.Environment["SENTRY_DSN"] = sentryDsn;
        startInfo.Environment["OXIMY_SESSION_ID"] = OximyLogger.SessionId;
        var oximyEnv = Environment.GetEnvironmentVariable("OXIMY_ENV") ?? "production";
        startInfo.Environment["OXIMY_ENV"] = oximyEnv;
        // Pass app version so addon can send X-Sensor-Version header
        startInfo.Environment["OXIMY_APP_VERSION"] = Constants.Version;

        _mitmProcess = new Process { StartInfo = startInfo };
        _mitmProcess.EnableRaisingEvents = true;
        _mitmProcess.Exited += OnProcessExited;

        // Buffer stderr/stdout so we can include them in error messages if process dies immediately
        var stderrLines = new ConcurrentQueue<string>();

        _mitmProcess.OutputDataReceived += (s, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
            {
                Debug.WriteLine($"[mitmdump] {e.Data}");
                OutputReceived?.Invoke(this, e.Data);
            }
        };
        _mitmProcess.ErrorDataReceived += (s, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
            {
                stderrLines.Enqueue(e.Data);
                Debug.WriteLine($"[mitmdump ERROR] {e.Data}");
                ErrorReceived?.Invoke(this, e.Data);
            }
        };

        Debug.WriteLine($"Starting mitmdump: {startInfo.FileName}");
        Debug.WriteLine($"Arguments: {startInfo.Arguments}");
        Debug.WriteLine($"Working Directory: {startInfo.WorkingDirectory}");
        Debug.WriteLine($"PYTHONHOME: {startInfo.Environment["PYTHONHOME"]}");
        Debug.WriteLine($"PYTHONPATH: {startInfo.Environment["PYTHONPATH"]}");

        try
        {
            _mitmProcess.Start();
            _mitmProcess.BeginOutputReadLine();
            _mitmProcess.BeginErrorReadLine();

            // Assign to Job Object to ensure cleanup on parent exit
            AssignProcessToJobObject(_mitmProcess);

            CurrentPort = port;
            _restartAttempts = 0;
            _intentionalStop = false;

            // Wait for mitmproxy to be ready (actually listening on the port)
            Debug.WriteLine($"[MitmService] Waiting for mitmproxy to start listening on port {port}...");
            var ready = await WaitForPortListeningAsync(port, timeoutSeconds: 10);

            if (_mitmProcess.HasExited)
            {
                // Give async stderr a moment to flush
                await Task.Delay(200);
                var stderrOutput = stderrLines.Count > 0
                    ? $"\nStderr:\n{string.Join("\n", stderrLines)}"
                    : "\n(No stderr captured - process died before output)";
                throw new MitmException($"mitmproxy exited immediately with code {_mitmProcess.ExitCode}{stderrOutput}");
            }

            if (!ready)
            {
                var stderrOutput = stderrLines.Count > 0
                    ? $"\nStderr:\n{string.Join("\n", stderrLines)}"
                    : "";
                throw new MitmException($"mitmproxy failed to start listening on port {port} within timeout{stderrOutput}");
            }

            Debug.WriteLine($"[MitmService] mitmproxy is ready and listening on port {port}");

            OximyLogger.Log(EventCode.MITM_START_002, "mitmproxy listening", new Dictionary<string, object>
            {
                ["port"] = port,
                ["pid"] = _mitmProcess.Id
            });
            OximyLogger.SetTag("mitm_running", "true");
            OximyLogger.SetTag("mitm_port", port.ToString());

            AppState.Instance.CurrentPort = port;
            AppState.Instance.ConnectionStatus = ConnectionStatus.Connected;
            Started?.Invoke(this, EventArgs.Empty);
        }
        catch (Exception ex)
        {
            OximyLogger.Log(EventCode.MITM_FAIL_304, "MITM process start failed",
                new Dictionary<string, object> { ["error"] = ex.Message });
            CurrentPort = null;
            AppState.Instance.ConnectionStatus = ConnectionStatus.Error;
            AppState.Instance.ErrorMessage = ex.Message;
            throw;
        }
    }

    /// <summary>
    /// Stop the mitmproxy process.
    /// </summary>
    public void Stop()
    {
        _intentionalStop = true;
        _restartCts?.Cancel();

        if (_mitmProcess != null)
        {
            try
            {
                if (!_mitmProcess.HasExited)
                {
                    _mitmProcess.Kill(entireProcessTree: true);
                    // Give addon time to complete final upload (typically 1-2s, max 3s)
                    Thread.Sleep(3000);
                }
            }
            catch
            {
                // Process may have already exited
            }
            finally
            {
                _mitmProcess.Dispose();
                _mitmProcess = null;
            }
        }

        // Kill ALL mitmproxy processes to catch any orphans/zombies
        KillAllMitmProcesses();

        CurrentPort = null;
        AppState.Instance.ConnectionStatus = ConnectionStatus.Disconnected;
        OximyLogger.Log(EventCode.MITM_STOP_001, "mitmproxy stopped normally");
        OximyLogger.SetTag("mitm_running", "false");
        Stopped?.Invoke(this, EventArgs.Empty);
    }

    /// <summary>
    /// Restart the mitmproxy process.
    /// </summary>
    public async Task RestartAsync()
    {
        Stop();
        await Task.Delay(500);
        await StartAsync();
    }

    /// <summary>
    /// Find an available port, starting from preferred port.
    /// </summary>
    private int FindAvailablePort()
    {
        // Try preferred port first
        if (IsPortAvailable(Constants.PreferredPort))
            return Constants.PreferredPort;

        // Search above and below
        for (int offset = 1; offset <= Constants.PortSearchRange; offset++)
        {
            if (IsPortAvailable(Constants.PreferredPort + offset))
                return Constants.PreferredPort + offset;
            if (IsPortAvailable(Constants.PreferredPort - offset))
                return Constants.PreferredPort - offset;
        }

        return 0;
    }

    private static bool IsPortAvailable(int port)
    {
        if (port < 1 || port > 65535)
            return false;

        try
        {
            using var listener = new TcpListener(IPAddress.Loopback, port);
            listener.Start();
            listener.Stop();
            return true;
        }
        catch (SocketException)
        {
            return false;
        }
    }

    /// <summary>
    /// Wait for mitmproxy to start listening on the specified port.
    /// This ensures the proxy is fully ready before we route traffic through it.
    /// </summary>
    private async Task<bool> WaitForPortListeningAsync(int port, int timeoutSeconds = 10)
    {
        var stopwatch = System.Diagnostics.Stopwatch.StartNew();
        var timeout = TimeSpan.FromSeconds(timeoutSeconds);

        while (stopwatch.Elapsed < timeout)
        {
            // Check if process has exited
            if (_mitmProcess == null || _mitmProcess.HasExited)
            {
                Debug.WriteLine("[MitmService] Process exited while waiting for port");
                return false;
            }

            // Try to connect to the port
            if (await IsPortListeningAsync(port))
            {
                Debug.WriteLine($"[MitmService] Port {port} is now accepting connections (took {stopwatch.ElapsedMilliseconds}ms)");
                return true;
            }

            // Wait a bit before retrying
            await Task.Delay(100);
        }

        Debug.WriteLine($"[MitmService] Timeout waiting for port {port} to accept connections");
        return false;
    }

    /// <summary>
    /// Check if a port is actively listening and accepting connections.
    /// Unlike IsPortAvailable, this checks if something IS listening, not if the port is free.
    /// </summary>
    private static async Task<bool> IsPortListeningAsync(int port)
    {
        try
        {
            using var client = new TcpClient();
            var connectTask = client.ConnectAsync(IPAddress.Loopback, port);
            var completed = await Task.WhenAny(connectTask, Task.Delay(500)) == connectTask;

            if (completed && client.Connected)
            {
                return true;
            }
        }
        catch (SocketException)
        {
            // Port not yet listening
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[MitmService] Error checking port: {ex.Message}");
        }

        return false;
    }

    private static string BuildArguments(int port)
    {
        var args = new List<string>
        {
            $"-s \"{Constants.AddonPath}\"",
            "--set oximy_enabled=true",
            $"--set \"oximy_output_dir={Constants.TracesDir}\"",
            // Use mitmproxy's default confdir (~/.mitmproxy) for certificates
            // This avoids certificate format/installation issues
            "--set oximy_manage_proxy=true",   // Python addon manages proxy based on sensor_enabled
            $"--mode regular@{port}",
            "--listen-host 127.0.0.1",
            "--ssl-insecure"
            // Note: -q (quiet) flag removed to enable error visibility for debugging
            // Add back once trace recording is confirmed working
        };

        return string.Join(" ", args);
    }

    private void OnProcessExited(object? sender, EventArgs e)
    {
        var exitCode = _mitmProcess?.ExitCode ?? -1;
        CurrentPort = null;

        Debug.WriteLine($"[MitmService] mitmproxy exited with code {exitCode}");

        // CRITICAL: Always disable proxy when mitmproxy stops to prevent internet blackhole.
        // This handles both normal exits and crashes.
        Debug.WriteLine("[MitmService] Process terminated, disabling proxy to prevent internet loss");
        try
        {
            App.ProxyService.DisableProxy();
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[MitmService] Failed to disable proxy on exit: {ex.Message}");
        }

        OximyLogger.SetTag("mitm_running", "false");

        // Only skip restart if Stop() was called intentionally or we're disposing
        if (_intentionalStop || _disposed)
        {
            Debug.WriteLine("[MitmService] Intentional stop - not restarting");
            AppState.Instance.ConnectionStatus = ConnectionStatus.Disconnected;
            Stopped?.Invoke(this, EventArgs.Empty);
            return;
        }

        // Unintentional exit (any exit code) — always restart
        var interpretation = exitCode switch
        {
            0 => "clean_exit",
            -1 => "unknown_or_killed",
            9 or 137 => "oom_or_force_kill",
            11 or 139 => "memory_corruption",
            15 or 143 => "normal_termination",
            6 or 134 => "abort",
            _ => "unknown"
        };
        OximyLogger.Log(EventCode.MITM_FAIL_306, "mitmproxy exited unexpectedly",
            new Dictionary<string, object>
            {
                ["exit_code"] = exitCode,
                ["interpretation"] = interpretation,
                ["restart_attempt"] = _restartAttempts,
                ["pid"] = _mitmProcess?.Id ?? -1
            },
            err: ("MitmException", "MITM_EXIT", $"Process exited with code {exitCode} ({interpretation})"));

        ScheduleRestart();
    }

    /// <summary>
    /// Schedule an automatic restart with exponential backoff.
    /// First 3 attempts: immediate (100ms). After that: exponential backoff up to 60s.
    /// Never gives up — keeps retrying until Stop() is called or app exits.
    /// </summary>
    private async void ScheduleRestart()
    {
        _restartAttempts++;

        // First 3 attempts: fast restart (100ms)
        // After that: exponential backoff capped at 60 seconds
        int delayMs;
        if (_restartAttempts <= 3)
        {
            delayMs = 100;
        }
        else
        {
            delayMs = Math.Min(60_000, (int)Math.Pow(2, _restartAttempts - 3) * 1000);
        }

        // Notify UI after fast retries are exhausted (but don't stop trying)
        if (_restartAttempts == Constants.MaxRestartAttempts + 1)
        {
            MaxRestartsExceeded?.Invoke(this, EventArgs.Empty);
        }

        OximyLogger.Log(EventCode.MITM_RETRY_001, "Restart scheduled",
            new Dictionary<string, object>
            {
                ["attempt"] = _restartAttempts,
                ["delay_ms"] = delayMs
            });

        Debug.WriteLine($"[MitmService] Restart attempt {_restartAttempts} in {delayMs}ms");

        AppState.Instance.ConnectionStatus = ConnectionStatus.Connecting;

        _restartCts?.Cancel();
        _restartCts = new CancellationTokenSource();

        try
        {
            await Task.Delay(delayMs, _restartCts.Token);
            await StartAsync();
            // Success — reset counter
            _restartAttempts = 0;
            Debug.WriteLine("[MitmService] Auto-restart successful");
        }
        catch (TaskCanceledException)
        {
            // Restart was cancelled (intentional Stop)
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[MitmService] Auto-restart failed: {ex.Message}");
            // Retry again with backoff — don't rely on OnProcessExited
            // (StartAsync may throw before process creation)
            if (!_intentionalStop && !_disposed)
            {
                ScheduleRestart();
            }
        }
    }

    #region Job Object (Process Group Management)

    /// <summary>
    /// Assign process to a Job Object so it gets killed when parent exits.
    /// This is critical on Windows to prevent orphaned mitmproxy processes.
    /// </summary>
    private void AssignProcessToJobObject(Process process)
    {
        if (_jobHandle == IntPtr.Zero)
        {
            _jobHandle = CreateJobObject(IntPtr.Zero, null);

            var info = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION
            {
                BasicLimitInformation = new JOBOBJECT_BASIC_LIMIT_INFORMATION
                {
                    LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                }
            };

            var infoSize = Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));
            var infoPtr = Marshal.AllocHGlobal(infoSize);

            try
            {
                Marshal.StructureToPtr(info, infoPtr, false);
                SetInformationJobObject(_jobHandle, JobObjectInfoType.ExtendedLimitInformation, infoPtr, (uint)infoSize);
            }
            finally
            {
                Marshal.FreeHGlobal(infoPtr);
            }
        }

        AssignProcessToJobObject(_jobHandle, process.Handle);
    }

    private const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000;

    private enum JobObjectInfoType
    {
        ExtendedLimitInformation = 9
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct JOBOBJECT_BASIC_LIMIT_INFORMATION
    {
        public long PerProcessUserTimeLimit;
        public long PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass;
        public uint SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct IO_COUNTERS
    {
        public ulong ReadOperationCount;
        public ulong WriteOperationCount;
        public ulong OtherOperationCount;
        public ulong ReadTransferCount;
        public ulong WriteTransferCount;
        public ulong OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION
    {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string? lpName);

    [DllImport("kernel32.dll")]
    private static extern bool AssignProcessToJobObject(IntPtr hJob, IntPtr hProcess);

    [DllImport("kernel32.dll")]
    private static extern bool SetInformationJobObject(IntPtr hJob, JobObjectInfoType infoType, IntPtr lpJobObjectInfo, uint cbJobObjectInfoLength);

    [DllImport("kernel32.dll")]
    private static extern bool CloseHandle(IntPtr hObject);

    #endregion

    public void Dispose()
    {
        if (_disposed)
            return;

        _disposed = true;
        _restartCts?.Cancel();
        _restartCts?.Dispose();

        Stop();

        if (_jobHandle != IntPtr.Zero)
        {
            CloseHandle(_jobHandle);
            _jobHandle = IntPtr.Zero;
        }
    }
}

/// <summary>
/// Exception thrown by MitmService operations.
/// </summary>
public class MitmException : Exception
{
    public MitmException(string message) : base(message) { }
    public MitmException(string message, Exception inner) : base(message, inner) { }
}
