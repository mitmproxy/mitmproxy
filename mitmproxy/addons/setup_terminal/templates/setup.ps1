$MITMPROXY_envVars = Get-ChildItem Env:

$Env:HTTP_PROXY = "{{ proxy_url }}"
$Env:HTTPS_PROXY = "{{ proxy_url }}"
$Env:http_proxy = "{{ proxy_url }}"
$Env:https_proxy = "{{ proxy_url }}"
$Env:WS_PROXY = "{{ proxy_url }}"
$Env:WSS_PROXY = "{{ proxy_url }}"
$Env:GLOBAL_AGENT_HTTP_PROXY = "{{ proxy_url }}"
$Env:CGI_HTTP_PROXY = "{{ proxy_url }}"
$Env:npm_config_proxy = "{{ proxy_url }}"
$Env:npm_config_https_proxy = "{{ proxy_url }}"
$Env:npm_config_scripts_prepend_node_path = "false"
$Env:SSL_CERT_FILE = "{{ cert_path }}"
$Env:NODE_EXTRA_CA_CERTS = "{{ cert_path }}"
$Env:DENO_CERT = "{{ cert_path }}"
$Env:PERL_LWP_SSL_CA_FILE = "{{ cert_path }}"
$Env:GIT_SSL_CAINFO = "{{ cert_path }}"
$Env:CARGO_HTTP_CAINFO = "{{ cert_path }}"
$Env:CURL_CA_BUNDLE = "{{ cert_path }}"
$Env:AWS_CA_BUNDLE = "{{ cert_path }}"
$Env:MITMPROXY_ACTIVE = "true"

function Stop-Intercepting {
    $currentEnvVars = Get-ChildItem Env:
    foreach ($envVar in $currentEnvVars) {
        [System.Environment]::SetEnvironmentVariable($envVar.Name, $null)
    }
    foreach ($var in $MITMPROXY_envVars) {
        [System.Environment]::SetEnvironmentVariable($var.Name, $var.Value)
    }
    $PSDefaultParameterValues.Remove("invoke-webrequest:proxy")
    $PSDefaultParameterValues.Remove("invoke-webrequest:SkipCertificateCheck")
    Write-Host 'mitmproxy interception disabled'
}

$PSDefaultParameterValues["invoke-webrequest:proxy"] = $Env:HTTP_PROXY
$PSDefaultParameterValues["invoke-webrequest:SkipCertificateCheck"] = $True

Write-Host "mitmproxy interception enabled`nTo stop intercepting type " -NoNewline
Write-Host "Stop-Intercepting" -ForegroundColor Red
