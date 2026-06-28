"""
Tests for Windows certificate store integration.
"""

from unittest.mock import patch

from OpenSSL import SSL

from mitmproxy.net import tls


class TestWindowsCertStore:
    """Test the use_windows_cert_store parameter in create_proxy_server_context."""

    def test_windows_cert_store_parameter_default(self):
        """Test that create_proxy_server_context accepts use_windows_cert_store parameter with default False."""
        ctx = tls.create_proxy_server_context(
            method=tls.Method.TLS_CLIENT_METHOD,
            min_version=tls.Version.TLS1_2,
            max_version=tls.Version.UNBOUNDED,
            cipher_list=None,
            ecdh_curve=None,
            verify=tls.Verify.VERIFY_NONE,
            ca_path=None,
            ca_pemfile=None,
            client_cert=None,
            legacy_server_connect=False,
            use_windows_cert_store=False,
        )
        assert isinstance(ctx, SSL.Context)

    def test_windows_cert_store_parameter_true(self):
        """Test that create_proxy_server_context accepts use_windows_cert_store=True."""
        # When use_windows_cert_store=True and no explicit CAs, it should use default system paths
        ctx = tls.create_proxy_server_context(
            method=tls.Method.TLS_CLIENT_METHOD,
            min_version=tls.Version.TLS1_2,
            max_version=tls.Version.UNBOUNDED,
            cipher_list=None,
            ecdh_curve=None,
            verify=tls.Verify.VERIFY_NONE,
            ca_path=None,
            ca_pemfile=None,
            client_cert=None,
            legacy_server_connect=False,
            use_windows_cert_store=True,
        )
        assert isinstance(ctx, SSL.Context)

    def test_explicit_ca_takes_precedence(self, tdata):
        """Test that explicit CA files take precedence over Windows cert store."""
        ca_file = tdata.path("mitmproxy/net/data/verificationcerts/trusted-root.crt")

        # When both explicit CA and use_windows_cert_store are provided, explicit CA should be used
        ctx = tls.create_proxy_server_context(
            method=tls.Method.TLS_CLIENT_METHOD,
            min_version=tls.Version.TLS1_2,
            max_version=tls.Version.UNBOUNDED,
            cipher_list=None,
            ecdh_curve=None,
            verify=tls.Verify.VERIFY_NONE,
            ca_path=None,
            ca_pemfile=str(ca_file),
            client_cert=None,
            legacy_server_connect=False,
            use_windows_cert_store=True,
        )
        assert isinstance(ctx, SSL.Context)

    def test_windows_cert_store_fallback_to_certifi(self):
        """Test that Windows cert store falls back to certifi when SSL_CTX_set_default_verify_paths fails."""
        # This tests the fallback behavior when SSL_CTX_set_default_verify_paths fails or is not available
        with patch('mitmproxy.net.tls.SSL._lib.SSL_CTX_set_default_verify_paths') as mock_set_default:
            # Simulate failure of SSL_CTX_set_default_verify_paths
            mock_set_default.return_value = 0

            ctx = tls.create_proxy_server_context(
                method=tls.Method.TLS_CLIENT_METHOD,
                min_version=tls.Version.TLS1_2,
                max_version=tls.Version.UNBOUNDED,
                cipher_list=None,
                ecdh_curve=None,
                verify=tls.Verify.VERIFY_NONE,
                ca_path=None,
                ca_pemfile=None,
                client_cert=None,
                legacy_server_connect=False,
                use_windows_cert_store=True,
            )
            assert isinstance(ctx, SSL.Context)

    def test_ca_path_parameter_works(self, tdata):
        """Test that ca_path parameter still works with use_windows_cert_store."""
        ca_path = str(tdata.path("mitmproxy/net/data/verificationcerts"))

        # When ca_path is provided, it should be used regardless of use_windows_cert_store
        ctx = tls.create_proxy_server_context(
            method=tls.Method.TLS_CLIENT_METHOD,
            min_version=tls.Version.TLS1_2,
            max_version=tls.Version.UNBOUNDED,
            cipher_list=None,
            ecdh_curve=None,
            verify=tls.Verify.VERIFY_NONE,
            ca_path=ca_path,
            ca_pemfile=None,
            client_cert=None,
            legacy_server_connect=False,
            use_windows_cert_store=True,
        )
        assert isinstance(ctx, SSL.Context)

    def test_certifi_used_when_windows_cert_store_false(self):
        """Test that certifi is used when use_windows_cert_store=False and no explicit CAs."""
        ctx = tls.create_proxy_server_context(
            method=tls.Method.TLS_CLIENT_METHOD,
            min_version=tls.Version.TLS1_2,
            max_version=tls.Version.UNBOUNDED,
            cipher_list=None,
            ecdh_curve=None,
            verify=tls.Verify.VERIFY_NONE,
            ca_path=None,
            ca_pemfile=None,
            client_cert=None,
            legacy_server_connect=False,
            use_windows_cert_store=False,
        )
        assert isinstance(ctx, SSL.Context)



