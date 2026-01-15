using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;

namespace OximyWindows.Services;

/// <summary>
/// Manages CA certificate generation and Windows certificate store installation.
/// Generates mitmproxy-compatible PEM certificates.
/// </summary>
public class CertificateService : INotifyPropertyChanged
{
    private bool _isCAGenerated;
    public bool IsCAGenerated
    {
        get => _isCAGenerated;
        private set => SetProperty(ref _isCAGenerated, value);
    }

    private bool _isCAInstalled;
    public bool IsCAInstalled
    {
        get => _isCAInstalled;
        private set => SetProperty(ref _isCAInstalled, value);
    }

    // Cache for certificate store lookup - expires after 30 seconds
    private DateTime _lastCertStoreCheck = DateTime.MinValue;
    private bool _cachedCertStoreResult;
    private static readonly TimeSpan CertStoreCacheExpiry = TimeSpan.FromSeconds(30);

    /// <summary>
    /// Check current certificate status.
    /// Uses cached result for cert store lookup to avoid expensive X509Store queries.
    /// </summary>
    public void CheckStatus()
    {
        IsCAGenerated = File.Exists(Constants.CACertPath) && File.Exists(Constants.CAKeyPath);
        IsCAInstalled = IsCAInCertStoreCached();
    }

    /// <summary>
    /// Force a fresh check of certificate status, bypassing cache.
    /// Call this after installing/uninstalling certificates.
    /// </summary>
    public void RefreshStatus()
    {
        _lastCertStoreCheck = DateTime.MinValue; // Invalidate cache
        CheckStatus();
    }

    /// <summary>
    /// Check if CA is in cert store, using cached result if available.
    /// </summary>
    private bool IsCAInCertStoreCached()
    {
        var now = DateTime.UtcNow;
        if (now - _lastCertStoreCheck < CertStoreCacheExpiry)
        {
            return _cachedCertStoreResult;
        }

        _cachedCertStoreResult = IsCAInCertStore();
        _lastCertStoreCheck = now;
        return _cachedCertStoreResult;
    }

    /// <summary>
    /// Check if our CA is installed in the Windows certificate store.
    /// </summary>
    private bool IsCAInCertStore()
    {
        // Try LocalMachine first (system-wide)
        try
        {
            using var store = new X509Store(StoreName.Root, StoreLocation.LocalMachine);
            store.Open(OpenFlags.ReadOnly);
            var certs = store.Certificates.Find(
                X509FindType.FindBySubjectName,
                Constants.CACommonName,
                validOnly: false);
            if (certs.Count > 0)
                return true;
        }
        catch (CryptographicException)
        {
            // No access to LocalMachine store
        }

        // Try CurrentUser as fallback
        try
        {
            using var store = new X509Store(StoreName.Root, StoreLocation.CurrentUser);
            store.Open(OpenFlags.ReadOnly);
            var certs = store.Certificates.Find(
                X509FindType.FindBySubjectName,
                Constants.CACommonName,
                validOnly: false);
            return certs.Count > 0;
        }
        catch (CryptographicException)
        {
            return false;
        }
    }

    /// <summary>
    /// Generate CA certificate using .NET cryptography APIs.
    /// Creates mitmproxy-compatible PEM files.
    /// </summary>
    public async Task GenerateCAAsync()
    {
        if (File.Exists(Constants.CACertPath) && File.Exists(Constants.CAKeyPath))
        {
            IsCAGenerated = true;
            return;
        }

        await Task.Run(() =>
        {
            Directory.CreateDirectory(Constants.OximyDir);

            // Generate RSA key pair (4096-bit for security)
            using var rsa = RSA.Create(4096);

            // Create certificate request
            var subjectName = new X500DistinguishedName(
                $"CN={Constants.CACommonName}, O={Constants.CAOrganization}, C={Constants.CACountry}");

            var request = new CertificateRequest(
                subjectName,
                rsa,
                HashAlgorithmName.SHA256,
                RSASignaturePadding.Pkcs1);

            // Add CA extensions
            request.CertificateExtensions.Add(
                new X509BasicConstraintsExtension(
                    certificateAuthority: true,
                    hasPathLengthConstraint: true,
                    pathLengthConstraint: 0,
                    critical: true));

            request.CertificateExtensions.Add(
                new X509KeyUsageExtension(
                    X509KeyUsageFlags.KeyCertSign | X509KeyUsageFlags.CrlSign,
                    critical: true));

            // Add Subject Key Identifier
            request.CertificateExtensions.Add(
                new X509SubjectKeyIdentifierExtension(request.PublicKey, critical: false));

            // Self-sign for 10 years
            var notBefore = DateTimeOffset.UtcNow;
            var notAfter = notBefore.AddDays(Constants.CAValidityDays);

            using var cert = request.CreateSelfSigned(notBefore, notAfter);

            // Export certificate (PEM format)
            var certPem = new StringBuilder();
            certPem.AppendLine("-----BEGIN CERTIFICATE-----");
            certPem.AppendLine(Convert.ToBase64String(cert.RawData, Base64FormattingOptions.InsertLineBreaks));
            certPem.AppendLine("-----END CERTIFICATE-----");
            File.WriteAllText(Constants.CACertPath, certPem.ToString());

            // Export private key (PEM format) - required by mitmproxy
            var keyPem = new StringBuilder();
            keyPem.AppendLine("-----BEGIN PRIVATE KEY-----");
            keyPem.AppendLine(Convert.ToBase64String(
                rsa.ExportPkcs8PrivateKey(),
                Base64FormattingOptions.InsertLineBreaks));
            keyPem.AppendLine("-----END PRIVATE KEY-----");

            // mitmproxy expects combined cert+key in mitmproxy-ca.pem
            var combinedPem = certPem.ToString() + keyPem.ToString();
            File.WriteAllText(Constants.CAKeyPath, combinedPem);

            // Also create separate cert file for installation
            File.WriteAllText(
                Path.Combine(Constants.OximyDir, "mitmproxy-ca-cert.pem"),
                certPem.ToString());
        });

        IsCAGenerated = true;
    }

    /// <summary>
    /// Install CA to Windows certificate store.
    /// Attempts LocalMachine first (requires elevation), falls back to CurrentUser.
    /// </summary>
    public async Task InstallCAAsync()
    {
        if (!IsCAGenerated)
            await GenerateCAAsync();

        var certPem = await File.ReadAllTextAsync(Constants.CACertPath);
        var certBytes = ConvertPemToDer(certPem);
        using var cert = new X509Certificate2(certBytes);

        // Try LocalMachine first (system-wide, requires admin)
        try
        {
            using var store = new X509Store(StoreName.Root, StoreLocation.LocalMachine);
            store.Open(OpenFlags.ReadWrite);
            store.Add(cert);
            store.Close();

            _lastCertStoreCheck = DateTime.MinValue; // Invalidate cache
            IsCAInstalled = true;
            Debug.WriteLine("CA installed to LocalMachine store");
            return;
        }
        catch (CryptographicException ex)
        {
            Debug.WriteLine($"Cannot install to LocalMachine: {ex.Message}");
            // Fall through to try elevation
        }

        // Try with elevation via certutil
        try
        {
            await InstallWithCertUtilAsync();
            IsCAInstalled = true;
            Debug.WriteLine("CA installed via certutil");
            return;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"certutil installation failed: {ex.Message}");
        }

        // Last resort: CurrentUser store (no elevation needed, but less coverage)
        try
        {
            using var store = new X509Store(StoreName.Root, StoreLocation.CurrentUser);
            store.Open(OpenFlags.ReadWrite);
            store.Add(cert);
            store.Close();

            _lastCertStoreCheck = DateTime.MinValue; // Invalidate cache
            IsCAInstalled = true;
            Debug.WriteLine("CA installed to CurrentUser store");
        }
        catch (CryptographicException ex)
        {
            throw new CertificateException($"Failed to install certificate: {ex.Message}", ex);
        }
    }

    /// <summary>
    /// Install certificate using certutil.exe with elevation.
    /// </summary>
    private async Task InstallWithCertUtilAsync()
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = "certutil.exe",
            Arguments = $"-addstore -user Root \"{Constants.CACertPath}\"",
            UseShellExecute = true,
            Verb = "runas", // Request elevation
            CreateNoWindow = true
        };

        using var process = Process.Start(startInfo);
        if (process == null)
            throw new CertificateException("Failed to start certutil");

        await process.WaitForExitAsync();

        if (process.ExitCode != 0)
            throw new CertificateException($"certutil failed with exit code {process.ExitCode}");
    }

    /// <summary>
    /// Remove CA from certificate store.
    /// </summary>
    public void RemoveCA()
    {
        foreach (var location in new[] { StoreLocation.LocalMachine, StoreLocation.CurrentUser })
        {
            try
            {
                using var store = new X509Store(StoreName.Root, location);
                store.Open(OpenFlags.ReadWrite);

                var certs = store.Certificates.Find(
                    X509FindType.FindBySubjectName,
                    Constants.CACommonName,
                    validOnly: false);

                foreach (var cert in certs)
                {
                    store.Remove(cert);
                }

                store.Close();
            }
            catch (CryptographicException ex)
            {
                Debug.WriteLine($"Cannot remove from {location}: {ex.Message}");
                // Continue trying other locations
            }
        }

        _lastCertStoreCheck = DateTime.MinValue; // Invalidate cache
        IsCAInstalled = false;
    }

    /// <summary>
    /// Delete CA files from disk.
    /// </summary>
    public void DeleteCAFiles()
    {
        try
        {
            if (File.Exists(Constants.CACertPath))
                File.Delete(Constants.CACertPath);

            if (File.Exists(Constants.CAKeyPath))
                File.Delete(Constants.CAKeyPath);

            var separateCertPath = Path.Combine(Constants.OximyDir, "mitmproxy-ca-cert.pem");
            if (File.Exists(separateCertPath))
                File.Delete(separateCertPath);

            IsCAGenerated = false;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"Failed to delete CA files: {ex.Message}");
        }
    }

    /// <summary>
    /// Convert PEM-encoded certificate to DER bytes.
    /// </summary>
    private static byte[] ConvertPemToDer(string pem)
    {
        var base64 = pem
            .Replace("-----BEGIN CERTIFICATE-----", "")
            .Replace("-----END CERTIFICATE-----", "")
            .Replace("\r", "")
            .Replace("\n", "");
        return Convert.FromBase64String(base64);
    }

    #region INotifyPropertyChanged

    public event PropertyChangedEventHandler? PropertyChanged;

    protected bool SetProperty<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
            return false;

        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        return true;
    }

    #endregion
}

/// <summary>
/// Exception thrown by CertificateService operations.
/// </summary>
public class CertificateException : Exception
{
    public CertificateException(string message) : base(message) { }
    public CertificateException(string message, Exception inner) : base(message, inner) { }
}
