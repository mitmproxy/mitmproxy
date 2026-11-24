set -gx HTTP_PROXY "{{ proxy_url }}"
set -gx HTTPS_PROXY "{{ proxy_url }}"
set -gx http_proxy "{{ proxy_url }}"
set -gx https_proxy "{{ proxy_url }}"
set -gx WS_PROXY "{{ proxy_url }}"
set -gx WSS_PROXY "{{ proxy_url }}"
set -gx GLOBAL_AGENT_HTTP_PROXY "{{ proxy_url }}"
set -gx CGI_HTTP_PROXY "{{ proxy_url }}"
set -gx npm_config_proxy "{{ proxy_url }}"
set -gx npm_config_https_proxy "{{ proxy_url }}"
set -gx npm_config_scripts_prepend_node_path "false"
set -gx SSL_CERT_FILE "{{ cert_path }}"
set -gx NODE_EXTRA_CA_CERTS "{{ cert_path }}"
set -gx DENO_CERT "{{ cert_path }}"
set -gx PERL_LWP_SSL_CA_FILE "{{ cert_path }}"
set -gx GIT_SSL_CAINFO "{{ cert_path }}"
set -gx CARGO_HTTP_CAINFO "{{ cert_path }}"
set -gx CURL_CA_BUNDLE "{{ cert_path }}"
set -gx AWS_CA_BUNDLE "{{ cert_path }}"
set -gx MITMPROXY_ACTIVE "true"

if command -v winpty >/dev/null 2>&1
    alias php=php
    alias node=node
end

echo 'mitmproxy interception enabled'
