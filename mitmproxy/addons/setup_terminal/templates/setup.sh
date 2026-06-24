export HTTP_PROXY="{{ proxy_url }}"
export HTTPS_PROXY="{{ proxy_url }}"
export http_proxy="{{ proxy_url }}"
export https_proxy="{{ proxy_url }}"
export WS_PROXY="{{ proxy_url }}"
export WSS_PROXY="{{ proxy_url }}"
export GLOBAL_AGENT_HTTP_PROXY="{{ proxy_url }}"
export CGI_HTTP_PROXY="{{ proxy_url }}"
export npm_config_proxy="{{ proxy_url }}"
export npm_config_https_proxy="{{ proxy_url }}"
export npm_config_scripts_prepend_node_path="false"
export SSL_CERT_FILE="{{ cert_path }}"
export NODE_EXTRA_CA_CERTS="{{ cert_path }}"
export DENO_CERT="{{ cert_path }}"
export PERL_LWP_SSL_CA_FILE="{{ cert_path }}"
export GIT_SSL_CAINFO="{{ cert_path }}"
export CARGO_HTTP_CAINFO="{{ cert_path }}"
export CURL_CA_BUNDLE="{{ cert_path }}"
export AWS_CA_BUNDLE="{{ cert_path }}"
export MITMPROXY_ACTIVE="true"

if command -v winpty >/dev/null 2>&1; then
    alias php=php
    alias node=node
fi

echo 'mitmproxy interception enabled'
