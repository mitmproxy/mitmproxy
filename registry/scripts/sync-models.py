#!/usr/bin/env python3
"""
Sync model data from models.dev API.

This script fetches the latest model pricing and capabilities from:
https://models.dev/api.json

And generates:
1. semconv/providers/_generated/models.yaml - Complete model registry
2. semconv/providers/_generated/models.json - JSON format for programmatic use
3. semconv/providers/_generated/models.ts - TypeScript types and helpers

Run this periodically (e.g., weekly via GitHub Action) to keep model data current.

Usage:
    python scripts/sync-models.py
    python scripts/sync-models.py --output-dir ./custom-output
    python scripts/sync-models.py --input-file /tmp/models.json  # Use local file
"""

import argparse
import json
import ssl
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen

# models.dev API URL
MODELS_DEV_URL = "https://models.dev/api.json"
MODELS_DEV_LOGOS_URL = "https://models.dev/logos"

# Provider ID mapping (models.dev id -> our canonical name)
# Most are 1:1, but some need normalization
PROVIDER_MAPPING = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google",
    "google-vertex": "google_vertex",
    "google-vertex-anthropic": "google_vertex_anthropic",
    "azure": "azure_openai",
    "amazon-bedrock": "aws_bedrock",
    "cohere": "cohere",
    "mistral": "mistral",
    "groq": "groq",
    "together-ai": "together",
    "fireworks-ai": "fireworks",
    "replicate": "replicate",
    "huggingface": "huggingface",
    "ollama-cloud": "ollama",
    "lmstudio": "lmstudio",
    "deepseek": "deepseek",
    "perplexity": "perplexity",
    "openrouter": "openrouter",
    "xai": "xai",
    "cerebras": "cerebras",
    "nvidia": "nvidia",
    "alibaba": "alibaba",
    "minimax": "minimax",
    "zhipu": "zhipu",
    "moonshot": "moonshot",
}

# Known API endpoints for providers (models.dev doesn't have all of these)
# These are used for traffic detection - matching outbound requests to providers
PROVIDER_API_ENDPOINTS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1",
    "google_vertex": "https://us-central1-aiplatform.googleapis.com/v1",
    "azure_openai": "https://*.openai.azure.com/openai",
    "aws_bedrock": "https://bedrock-runtime.*.amazonaws.com",
    "cohere": "https://api.cohere.ai/v1",
    "mistral": "https://api.mistral.ai/v1",
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "replicate": "https://api.replicate.com/v1",
    "huggingface": "https://api-inference.huggingface.co",
    "deepseek": "https://api.deepseek.com/v1",
    "perplexity": "https://api.perplexity.ai",
    "openrouter": "https://openrouter.ai/api/v1",
    "xai": "https://api.x.ai/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
    "alibaba": "https://dashscope.aliyuncs.com/api/v1",
    "minimax": "https://api.minimax.chat/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "moonshot": "https://api.moonshot.cn/v1",
}

# API format overrides - only 5 providers use non-OpenAI format
# Everything else defaults to "openai" format (69+ providers)
API_FORMAT_OVERRIDES = {
    "anthropic": "anthropic",
    "google": "google",
    "google_vertex": "google",
    "google_vertex_anthropic": "anthropic",
    "aws_bedrock": "bedrock",
    "cohere": "cohere",
}

# Domain patterns for wildcard matching (Azure, Bedrock)
DOMAIN_PATTERNS = [
    {"pattern": r".*\.openai\.azure\.com$", "provider": "azure_openai"},
    {"pattern": r"bedrock-runtime\..*\.amazonaws\.com$", "provider": "aws_bedrock"},
    {"pattern": r"bedrock\..*\.amazonaws\.com$", "provider": "aws_bedrock"},
]

# Parser definitions - JSONPath rules for extracting data from HTTP requests/responses
# These are stable API contracts that rarely change
PARSERS = {
    "openai": {
        "request": {
            "model": "$.model",
            "messages": "$.messages",
            "stream": "$.stream",
            "max_tokens": "$.max_tokens",
            "temperature": "$.temperature",
            "tools": "$.tools",
            "tool_choice": "$.tool_choice",
        },
        "response": {
            "model": "$.model",
            "usage": {
                "prompt_tokens": "$.usage.prompt_tokens",
                "completion_tokens": "$.usage.completion_tokens",
                "total_tokens": "$.usage.total_tokens",
            },
            "finish_reason": "$.choices[0].finish_reason",
            "content": "$.choices[0].message.content",
        },
        "streaming": {
            "format": "sse",
            "done_signal": "[DONE]",
            "delta_path": "$.choices[0].delta",
        },
    },
    "anthropic": {
        "request": {
            "model": "$.model",
            "messages": "$.messages",
            "system": "$.system",
            "max_tokens": "$.max_tokens",
            "temperature": "$.temperature",
            "stream": "$.stream",
            "tools": "$.tools",
            "tool_choice": "$.tool_choice",
        },
        "response": {
            "model": "$.model",
            "usage": {
                "input_tokens": "$.usage.input_tokens",
                "output_tokens": "$.usage.output_tokens",
                "cache_creation_input_tokens": "$.usage.cache_creation_input_tokens",
                "cache_read_input_tokens": "$.usage.cache_read_input_tokens",
            },
            "stop_reason": "$.stop_reason",
            "content": "$.content",
        },
        "streaming": {
            "format": "sse",
            "done_signal": "message_stop",
            "delta_path": "$.delta",
        },
    },
    "google": {
        "request": {
            "model": "{url_path}",  # Model extracted from URL path
            "contents": "$.contents",
            "system_instruction": "$.systemInstruction",
            "generation_config": {
                "temperature": "$.generationConfig.temperature",
                "max_output_tokens": "$.generationConfig.maxOutputTokens",
                "top_p": "$.generationConfig.topP",
                "top_k": "$.generationConfig.topK",
            },
            "tools": "$.tools",
        },
        "response": {
            "usage": {
                "prompt_tokens": "$.usageMetadata.promptTokenCount",
                "completion_tokens": "$.usageMetadata.candidatesTokenCount",
                "total_tokens": "$.usageMetadata.totalTokenCount",
            },
            "finish_reason": "$.candidates[0].finishReason",
            "content": "$.candidates[0].content",
        },
        "streaming": {
            "format": "sse",
            "done_signal": None,
        },
    },
    "bedrock": {
        "request": {
            "model": "$.modelId",
            "messages": "$.messages",
            "system": "$.system",
            "max_tokens": "$.max_tokens",
            "temperature": "$.temperature",
        },
        "response": {
            "model": "$.modelId",
            "usage": {
                "input_tokens": "$.usage.inputTokens",
                "output_tokens": "$.usage.outputTokens",
                "total_tokens": "$.usage.totalTokens",
            },
            "stop_reason": "$.stopReason",
            "content": "$.output.message.content",
        },
        "streaming": {
            "format": "sse",
            "done_signal": None,
        },
    },
    "cohere": {
        "request": {
            "model": "$.model",
            "message": "$.message",
            "chat_history": "$.chat_history",
            "temperature": "$.temperature",
            "max_tokens": "$.max_tokens",
            "stream": "$.stream",
        },
        "response": {
            "usage": {
                "input_tokens": "$.meta.tokens.input_tokens",
                "output_tokens": "$.meta.tokens.output_tokens",
            },
            "finish_reason": "$.finish_reason",
            "content": "$.text",
        },
        "streaming": {
            "format": "sse",
            "done_signal": None,
        },
    },
}


def get_api_format(provider_id: str) -> str:
    """Get the API format for a provider. Defaults to 'openai' for most providers."""
    return API_FORMAT_OVERRIDES.get(provider_id, "openai")


def extract_domain(api_endpoint: str) -> str | None:
    """Extract domain from API endpoint URL."""
    if not api_endpoint:
        return None
    try:
        from urllib.parse import urlparse

        parsed = urlparse(api_endpoint)
        return parsed.netloc
    except Exception:
        return None


def build_domain_lookup(providers: dict) -> dict:
    """Build domain → provider_id lookup from API endpoints."""
    lookup = {}
    for provider_id, provider in providers.items():
        domain = extract_domain(provider.get("api_endpoint"))
        if domain and "*" not in domain:  # Skip wildcard domains
            lookup[domain] = provider_id
    return lookup


# Capability mapping from models.dev fields to OISP capabilities
CAPABILITY_MAPPING = {
    "reasoning": "reasoning",
    "tool_call": "function_calling",
    "attachment": "vision",  # attachment often means file/image support
    "structured_output": "json_mode",
    "temperature": "temperature",
}

# Modality input to capability mapping
INPUT_MODALITY_CAPABILITIES = {
    "image": "vision",
    "audio": "audio_input",
    "video": "video_input",
    "pdf": "pdf_input",
}

OUTPUT_MODALITY_CAPABILITIES = {
    "audio": "audio_output",
    "image": "image_output",
}


def fetch_models_dev_data(local_file: Path | None = None) -> dict:
    """Fetch the latest model data from models.dev or load from local file."""
    if local_file and local_file.exists():
        print(f"Loading model data from {local_file}...")
        with open(local_file) as f:
            data = json.load(f)
        print(f"Loaded {len(data)} providers")
        return data

    print(f"Fetching model data from {MODELS_DEV_URL}...")
    try:
        # Create SSL context
        ctx = ssl.create_default_context()

        req = Request(MODELS_DEV_URL, headers={"User-Agent": "OISP-Sync/1.0"})
        with urlopen(req, timeout=30, context=ctx) as response:
            data = json.loads(response.read().decode("utf-8"))
        print(f"Fetched {len(data)} providers")
        return data
    except URLError as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        print("Try downloading manually and using --input-file:", file=sys.stderr)
        print(f"  curl -sL '{MODELS_DEV_URL}' -o /tmp/models.json", file=sys.stderr)
        print(
            f"  python scripts/sync-models.py --input-file /tmp/models.json",
            file=sys.stderr,
        )
        sys.exit(1)


def extract_capabilities(model_data: dict) -> list[str]:
    """Extract capabilities from models.dev model entry."""
    capabilities = []

    # Direct capability flags
    for models_dev_cap, oisp_cap in CAPABILITY_MAPPING.items():
        if model_data.get(models_dev_cap):
            if oisp_cap not in capabilities:
                capabilities.append(oisp_cap)

    # Input modalities
    modalities = model_data.get("modalities", {})
    for input_mod in modalities.get("input", []):
        if input_mod in INPUT_MODALITY_CAPABILITIES:
            cap = INPUT_MODALITY_CAPABILITIES[input_mod]
            if cap not in capabilities:
                capabilities.append(cap)

    # Output modalities
    for output_mod in modalities.get("output", []):
        if output_mod in OUTPUT_MODALITY_CAPABILITIES:
            cap = OUTPUT_MODALITY_CAPABILITIES[output_mod]
            if cap not in capabilities:
                capabilities.append(cap)

    return sorted(capabilities)


def determine_mode(model_data: dict) -> str:
    """Determine the model mode from modalities."""
    modalities = model_data.get("modalities", {})
    outputs = modalities.get("output", [])

    if "image" in outputs:
        return "image"
    if "audio" in outputs and "text" not in outputs:
        return "audio_speech"

    # Check model ID patterns for embeddings
    model_id = model_data.get("id", "").lower()
    if "embed" in model_id:
        return "embedding"
    if "rerank" in model_id:
        return "rerank"
    if "transcription" in model_id or "whisper" in model_id:
        return "audio_transcription"
    if "moderation" in model_id:
        return "moderation"

    return "chat"


def parse_provider(
    provider_id: str, provider_data: dict
) -> tuple[str, dict, list[dict]]:
    """Parse a provider entry from models.dev format to OISP format.

    Returns: (canonical_provider_id, provider_info, models_list)
    """
    # Map to canonical provider ID
    canonical_id = PROVIDER_MAPPING.get(provider_id, provider_id.replace("-", "_"))

    # Get API endpoint - prefer models.dev data, fall back to our known endpoints
    api_endpoint = provider_data.get("api")
    if not api_endpoint:
        api_endpoint = PROVIDER_API_ENDPOINTS.get(canonical_id)

    # Provider info
    provider_info = {
        "id": canonical_id,
        "models_dev_id": provider_id,
        "name": provider_data.get("name", provider_id),
        "api_endpoint": api_endpoint,
        "documentation": provider_data.get("doc"),
        "env_vars": provider_data.get("env", []),
        "logo_url": f"{MODELS_DEV_LOGOS_URL}/{provider_id}.svg",
    }

    # Parse models
    models = []
    models_data = provider_data.get("models", {})

    for model_id, model_data in models_data.items():
        model_info = parse_model(canonical_id, model_id, model_data)
        if model_info:
            models.append(model_info)

    return canonical_id, provider_info, models


def parse_model(provider_id: str, model_id: str, model_data: dict) -> dict | None:
    """Parse a single model entry from models.dev format to OISP format."""
    # Build model info
    model_info = {
        "id": model_id,
        "provider": provider_id,
        "name": model_data.get("name", model_id),
        "family": model_data.get("family"),
        "mode": determine_mode(model_data),
    }

    # Context limits
    limits = model_data.get("limit", {})
    if "context" in limits:
        model_info["max_input_tokens"] = limits["context"]
    if "output" in limits:
        model_info["max_output_tokens"] = limits["output"]

    # Pricing (models.dev uses $/1M tokens, we use $/1K tokens)
    cost = model_data.get("cost", {})
    if "input" in cost and cost["input"] is not None:
        # Convert from $/1M to $/1K
        model_info["input_cost_per_1k"] = round(cost["input"] / 1000, 8)
    if "output" in cost and cost["output"] is not None:
        model_info["output_cost_per_1k"] = round(cost["output"] / 1000, 8)

    # Cache pricing
    if "cache_read" in cost and cost["cache_read"] is not None:
        model_info["cache_read_cost_per_1k"] = round(cost["cache_read"] / 1000, 8)
    if "cache_write" in cost and cost["cache_write"] is not None:
        model_info["cache_write_cost_per_1k"] = round(cost["cache_write"] / 1000, 8)

    # Reasoning token pricing (for o1-style models)
    if "reasoning" in cost and cost["reasoning"] is not None:
        model_info["reasoning_cost_per_1k"] = round(cost["reasoning"] / 1000, 8)

    # Capabilities
    capabilities = extract_capabilities(model_data)
    if capabilities:
        model_info["capabilities"] = capabilities

    # Knowledge cutoff
    if "knowledge" in model_data:
        model_info["knowledge_cutoff"] = model_data["knowledge"]

    # Release info
    if "release_date" in model_data:
        model_info["release_date"] = model_data["release_date"]

    # Open weights
    if model_data.get("open_weights"):
        model_info["open_weights"] = True

    # Deprecation status
    status = model_data.get("status", "")
    if status == "deprecated":
        model_info["deprecated"] = True

    return model_info


def generate_yaml(providers: dict, models_by_provider: dict, output_path: Path):
    """Generate YAML output."""
    lines = [
        "# OISP Model Registry",
        "# Auto-generated from models.dev - DO NOT EDIT MANUALLY",
        f"# Source: {MODELS_DEV_URL}",
        f"# Generated: {datetime.now(timezone.utc).isoformat()}",
        "#",
        "# To regenerate: python scripts/sync-models.py",
        "",
        "version: '0.1'",
        f"generated_at: '{datetime.now(timezone.utc).isoformat()}'",
        "source: models.dev",
        f"source_url: '{MODELS_DEV_URL}'",
        "",
        "providers:",
    ]

    for provider_id in sorted(providers.keys()):
        provider = providers[provider_id]
        models = models_by_provider.get(provider_id, [])

        lines.append(f"  {provider_id}:")
        lines.append(f"    name: '{provider['name']}'")
        if provider.get("api_endpoint"):
            lines.append(f"    api_endpoint: '{provider['api_endpoint']}'")
        if provider.get("logo_url"):
            lines.append(f"    logo_url: '{provider['logo_url']}'")
        lines.append(f"    model_count: {len(models)}")
        lines.append("    models:")

        for model in sorted(models, key=lambda m: m.get("id", "")):
            model_id = model["id"]
            lines.append(f"      '{model_id}':")

            if model.get("name") and model["name"] != model_id:
                lines.append(f"        name: '{model['name']}'")

            if model.get("family"):
                lines.append(f"        family: '{model['family']}'")

            if "mode" in model:
                lines.append(f"        mode: {model['mode']}")

            if "max_input_tokens" in model:
                lines.append(f"        max_input_tokens: {model['max_input_tokens']}")

            if "max_output_tokens" in model:
                lines.append(f"        max_output_tokens: {model['max_output_tokens']}")

            if "input_cost_per_1k" in model:
                lines.append(f"        input_cost_per_1k: {model['input_cost_per_1k']}")

            if "output_cost_per_1k" in model:
                lines.append(
                    f"        output_cost_per_1k: {model['output_cost_per_1k']}"
                )

            if "cache_read_cost_per_1k" in model:
                lines.append(
                    f"        cache_read_cost_per_1k: {model['cache_read_cost_per_1k']}"
                )

            if "cache_write_cost_per_1k" in model:
                lines.append(
                    f"        cache_write_cost_per_1k: {model['cache_write_cost_per_1k']}"
                )

            if "capabilities" in model:
                caps = ", ".join(model["capabilities"])
                lines.append(f"        capabilities: [{caps}]")

            if model.get("knowledge_cutoff"):
                lines.append(f"        knowledge_cutoff: '{model['knowledge_cutoff']}'")

            if model.get("open_weights"):
                lines.append("        open_weights: true")

            if model.get("deprecated"):
                lines.append("        deprecated: true")

    output_path.write_text("\n".join(lines) + "\n")
    print(f"Generated: {output_path}")


def generate_json(
    providers: dict, models_by_provider: dict, all_models: list[dict], output_path: Path
):
    """Generate JSON output with parsers, domain_lookup, and api_format."""
    total_models = sum(len(models) for models in models_by_provider.values())

    # Build domain lookup from provider endpoints
    domain_lookup = build_domain_lookup(providers)

    output = {
        "version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "models.dev",
        "source_url": MODELS_DEV_URL,
        "logos_url": MODELS_DEV_LOGOS_URL,
        "stats": {
            "total_models": total_models,
            "providers": len(providers),
            "api_formats": len(set(get_api_format(p) for p in providers.keys())),
        },
        "providers": {},
        "models": {},
        # New fields for spec-driven parsing
        "parsers": PARSERS,
        "domain_lookup": domain_lookup,
        "domain_patterns": DOMAIN_PATTERNS,
    }

    # Provider details with api_format
    for provider_id in sorted(providers.keys()):
        provider = providers[provider_id]
        models = models_by_provider.get(provider_id, [])
        output["providers"][provider_id] = {
            "name": provider["name"],
            "api_endpoint": provider.get("api_endpoint"),
            "api_format": get_api_format(provider_id),  # Add API format
            "documentation": provider.get("documentation"),
            "env_vars": provider.get("env_vars", []),
            "logo_url": provider.get("logo_url"),
            "model_count": len(models),
            "models": [m["id"] for m in sorted(models, key=lambda m: m["id"])],
        }

    # Flat model lookup
    for model in all_models:
        key = f"{model['provider']}/{model['id']}"
        output["models"][key] = model

    output_path.write_text(json.dumps(output, indent=2) + "\n")
    print(f"Generated: {output_path}")
    print(f"  - {len(domain_lookup)} domains mapped to providers")
    print(f"  - {len(PARSERS)} API format parsers included")


def generate_typescript_types(providers: dict, output_path: Path):
    """Generate TypeScript type definitions for the model registry."""
    # Generate provider union type from actual providers
    provider_ids = sorted(providers.keys())
    provider_union = "\n  | ".join(
        [f"'{p}'" for p in provider_ids[:20]]
    )  # Top 20 for readability

    content = f"""// OISP Model Registry Types
// Auto-generated from models.dev - DO NOT EDIT MANUALLY
// Source: {MODELS_DEV_URL}
// Generated: {datetime.now(timezone.utc).isoformat()}

export type AIProvider =
  | {provider_union}
  | string;

export type ModelMode =
  | 'chat'
  | 'completion'
  | 'embedding'
  | 'image'
  | 'audio_transcription'
  | 'audio_speech'
  | 'moderation'
  | 'rerank';

export type ModelCapability =
  | 'vision'
  | 'function_calling'
  | 'json_mode'
  | 'reasoning'
  | 'temperature'
  | 'audio_input'
  | 'audio_output'
  | 'video_input'
  | 'image_output'
  | 'pdf_input';

export interface ModelInfo {{
  id: string;
  provider: AIProvider;
  name?: string;
  family?: string;
  mode: ModelMode;
  max_input_tokens?: number;
  max_output_tokens?: number;
  input_cost_per_1k?: number;
  output_cost_per_1k?: number;
  cache_read_cost_per_1k?: number;
  cache_write_cost_per_1k?: number;
  reasoning_cost_per_1k?: number;
  capabilities?: ModelCapability[];
  knowledge_cutoff?: string;
  release_date?: string;
  open_weights?: boolean;
  deprecated?: boolean;
}}

export interface ProviderInfo {{
  name: string;
  api_endpoint?: string;
  api_format: ApiFormat;
  documentation?: string;
  env_vars: string[];
  logo_url?: string;
  model_count: number;
  models: string[];
}}

export type ApiFormat = 'openai' | 'anthropic' | 'google' | 'bedrock' | 'cohere';

export interface UsageExtraction {{
  prompt_tokens?: string;
  completion_tokens?: string;
  total_tokens?: string;
  input_tokens?: string;
  output_tokens?: string;
  cache_creation_input_tokens?: string;
  cache_read_input_tokens?: string;
}}

export interface RequestParser {{
  model: string;
  messages?: string;
  contents?: string;
  system?: string;
  system_instruction?: string;
  max_tokens?: string;
  temperature?: string;
  stream?: string;
  tools?: string;
  tool_choice?: string;
  generation_config?: Record<string, string>;
  message?: string;
  chat_history?: string;
}}

export interface ResponseParser {{
  model?: string;
  usage: UsageExtraction;
  finish_reason?: string;
  stop_reason?: string;
  content?: string;
}}

export interface StreamingParser {{
  format: 'sse';
  done_signal: string | null;
  delta_path?: string;
}}

export interface Parser {{
  request: RequestParser;
  response: ResponseParser;
  streaming?: StreamingParser;
}}

export interface DomainPattern {{
  pattern: string;
  provider: string;
}}

export interface ModelRegistry {{
  version: string;
  generated_at: string;
  source: string;
  source_url: string;
  logos_url: string;
  stats: {{
    total_models: number;
    providers: number;
    api_formats: number;
  }};
  providers: Record<AIProvider, ProviderInfo>;
  models: Record<string, ModelInfo>;
  parsers: Record<ApiFormat, Parser>;
  domain_lookup: Record<string, string>;
  domain_patterns: DomainPattern[];
}}

/**
 * Lookup a model by provider and model ID.
 */
export function lookupModel(
  registry: ModelRegistry,
  provider: AIProvider,
  modelId: string
): ModelInfo | undefined {{
  return registry.models[`${{provider}}/${{modelId}}`];
}}

/**
 * Get provider info including API endpoint for detection.
 */
export function getProvider(
  registry: ModelRegistry,
  providerId: AIProvider
): ProviderInfo | undefined {{
  return registry.providers[providerId];
}}

/**
 * Find provider by domain name.
 * First tries exact domain lookup, then pattern matching for wildcards.
 */
export function findProviderByDomain(
  registry: ModelRegistry,
  domain: string
): {{ providerId: AIProvider; provider: ProviderInfo }} | undefined {{
  // Try exact domain lookup first
  const providerId = registry.domain_lookup[domain];
  if (providerId && registry.providers[providerId]) {{
    return {{ providerId: providerId as AIProvider, provider: registry.providers[providerId] }};
  }}

  // Try pattern matching for wildcards (Azure, Bedrock)
  for (const pattern of registry.domain_patterns) {{
    if (new RegExp(pattern.pattern).test(domain)) {{
      const matchedProvider = registry.providers[pattern.provider];
      if (matchedProvider) {{
        return {{ providerId: pattern.provider as AIProvider, provider: matchedProvider }};
      }}
    }}
  }}

  return undefined;
}}

/**
 * Find provider by full URL.
 * Extracts domain from URL and uses findProviderByDomain.
 */
export function findProviderByEndpoint(
  registry: ModelRegistry,
  url: string
): {{ providerId: AIProvider; provider: ProviderInfo }} | undefined {{
  try {{
    const domain = new URL(url).hostname;
    return findProviderByDomain(registry, domain);
  }} catch {{
    return undefined;
  }}
}}

/**
 * Get the parser for a provider's API format.
 */
export function getParser(
  registry: ModelRegistry,
  providerId: AIProvider
): Parser | undefined {{
  const provider = registry.providers[providerId];
  if (!provider) return undefined;
  return registry.parsers[provider.api_format];
}}

/**
 * Get the API format for a provider.
 */
export function getApiFormat(
  registry: ModelRegistry,
  providerId: AIProvider
): ApiFormat | undefined {{
  return registry.providers[providerId]?.api_format;
}}

/**
 * Estimate the cost of an API call.
 */
export function estimateCost(
  model: ModelInfo,
  inputTokens: number,
  outputTokens: number,
  options?: {{
    cachedInputTokens?: number;
    reasoningTokens?: number;
  }}
): {{ input: number; output: number; cached?: number; reasoning?: number; total: number }} | undefined {{
  if (!model.input_cost_per_1k && !model.output_cost_per_1k) {{
    return undefined;
  }}

  const input = model.input_cost_per_1k
    ? (inputTokens / 1000) * model.input_cost_per_1k
    : 0;
  const output = model.output_cost_per_1k
    ? (outputTokens / 1000) * model.output_cost_per_1k
    : 0;

  let cached = 0;
  if (options?.cachedInputTokens && model.cache_read_cost_per_1k) {{
    cached = (options.cachedInputTokens / 1000) * model.cache_read_cost_per_1k;
  }}

  let reasoning = 0;
  if (options?.reasoningTokens && model.reasoning_cost_per_1k) {{
    reasoning = (options.reasoningTokens / 1000) * model.reasoning_cost_per_1k;
  }}

  const total = input + output + cached + reasoning;

  const result: any = {{
    input: Math.round(input * 1000000) / 1000000,
    output: Math.round(output * 1000000) / 1000000,
    total: Math.round(total * 1000000) / 1000000,
  }};

  if (cached > 0) result.cached = Math.round(cached * 1000000) / 1000000;
  if (reasoning > 0) result.reasoning = Math.round(reasoning * 1000000) / 1000000;

  return result;
}}

/**
 * Get the logo URL for a provider.
 */
export function getProviderLogoUrl(providerId: string): string {{
  return `{MODELS_DEV_LOGOS_URL}/${{providerId}}.svg`;
}}
"""
    output_path.write_text(content)
    print(f"Generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Sync model data from models.dev")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent / "providers" / "_generated",
        help="Output directory for generated files",
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=None,
        help="Local JSON file to use instead of fetching from URL",
    )
    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch data
    raw_data = fetch_models_dev_data(args.input_file)

    # Parse providers and models
    providers = {}
    models_by_provider = {}
    all_models = []

    for provider_id, provider_data in raw_data.items():
        canonical_id, provider_info, models = parse_provider(provider_id, provider_data)
        providers[canonical_id] = provider_info
        models_by_provider[canonical_id] = models
        all_models.extend(models)

    print(f"Parsed {len(all_models)} models from {len(providers)} providers")

    # Generate outputs
    generate_yaml(providers, models_by_provider, args.output_dir / "models.yaml")
    generate_json(
        providers, models_by_provider, all_models, args.output_dir / "models.json"
    )
    generate_typescript_types(providers, args.output_dir / "models.ts")

    # Print summary
    print("\nProvider Summary (top 20 by model count):")
    sorted_providers = sorted(
        models_by_provider.items(), key=lambda x: len(x[1]), reverse=True
    )[:20]
    for provider_id, models in sorted_providers:
        print(f"  {provider_id}: {len(models)} models")

    print(f"\nTotal: {len(all_models)} models from {len(providers)} providers")


if __name__ == "__main__":
    main()
