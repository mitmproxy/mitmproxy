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
/// Handles port finding, process spawning, crash recovery with exponential backoff.
/// </summary>
public class MitmService : IDisposable
{
    private Process? _mitmProcess;
    private IntPtr _jobHandle = IntPtr.Zero;
    private CancellationTokenSource? _restartCts;
    private int _restartAttempts;
    private bool _disposed;

    public int? CurrentPort { get; private set; }
    public bool IsRunning => _mitmProcess is { HasExited: false };

    public event EventHandler? Started;
    public event EventHandler? Stopped;
    public event EventHandler? MaxRestartsExceeded;
    public event EventHandler<string>? OutputReceived;
    public event EventHandler<string>? ErrorReceived;

    /// <summary>
    /// Start the mitmproxy process.
    /// </summary>
    public async Task StartAsync()
    {
        if (IsRunning)
            return;

        var port = FindAvailablePort();
        if (port == 0)
            throw new MitmException("No available port found in range");

        // Ensure CA certificate exists
        if (!File.Exists(Constants.CACertPath))
            throw new MitmException("CA certificate not found. Please install certificate first.");

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

        _mitmProcess = new Process { StartInfo = startInfo };
        _mitmProcess.EnableRaisingEvents = true;
        _mitmProcess.Exited += OnProcessExited;
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

            // Wait for mitmproxy to be ready (actually listening on the port)
            Debug.WriteLine($"[MitmService] Waiting for mitmproxy to start listening on port {port}...");
            var ready = await WaitForPortListeningAsync(port, timeoutSeconds: 10);

            if (_mitmProcess.HasExited)
            {
                throw new MitmException($"mitmproxy exited immediately with code {_mitmProcess.ExitCode}");
            }

            if (!ready)
            {
                throw new MitmException($"mitmproxy failed to start listening on port {port} within timeout");
            }

            Debug.WriteLine($"[MitmService] mitmproxy is ready and listening on port {port}");

            AppState.Instance.CurrentPort = port;
            AppState.Instance.ConnectionStatus = ConnectionStatus.Connected;
            Started?.Invoke(this, EventArgs.Empty);
        }
        catch (Exception ex)
        {
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
        _restartCts?.Cancel();

        if (_mitmProcess != null)
        {
            try
            {
                if (!_mitmProcess.HasExited)
                {
                    _mitmProcess.Kill(entireProcessTree: true);
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

        CurrentPort = null;
        AppState.Instance.ConnectionStatus = ConnectionStatus.Disconnected;
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
            $"--set \"confdir={Constants.OximyDir}\"",
            "--set oximy_manage_proxy=false",  // C# app handles proxy configuration
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

        Debug.WriteLine($"mitmproxy exited with code {exitCode}");

        // Check if this was a crash (not a clean exit or termination by us)
        if (exitCode != 0 && exitCode != -1 && !_disposed)
        {
            ScheduleRestart();
        }
        else
        {
            AppState.Instance.ConnectionStatus = ConnectionStatus.Disconnected;
            Stopped?.Invoke(this, EventArgs.Empty);
        }
    }

    private async void ScheduleRestart()
    {
        if (_restartAttempts >= Constants.MaxRestartAttempts)
        {
            AppState.Instance.ConnectionStatus = ConnectionStatus.Error;
            AppState.Instance.ErrorMessage = "mitmproxy crashed too many times. Please restart Oximy.";
            MaxRestartsExceeded?.Invoke(this, EventArgs.Empty);
            return;
        }

        _restartAttempts++;
        var delaySeconds = (int)Math.Pow(2, _restartAttempts); // 2, 4, 8 seconds

        Debug.WriteLine($"Scheduling restart attempt {_restartAttempts} in {delaySeconds}s");

        AppState.Instance.ConnectionStatus = ConnectionStatus.Connecting;

        _restartCts?.Cancel();
        _restartCts = new CancellationTokenSource();

        try
        {
            await Task.Delay(TimeSpan.FromSeconds(delaySeconds), _restartCts.Token);
            await StartAsync();
        }
        catch (TaskCanceledException)
        {
            // Restart was cancelled
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"Restart failed: {ex.Message}");
            // Will trigger another restart via OnProcessExited
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
