"""
Enforcement engine for Oximy MITM proxy.

Detects PII and sensitive data in request bodies and enforces
redaction/warn/block policies. Uses Microsoft Presidio for high-accuracy
PII detection with built-in Luhn validation, NER-based entity recognition,
and confidence scoring. Falls back to regex patterns when Presidio is not
available.

Primary mechanism: **in-flight PII redaction** -- PII is replaced with
[REDACTED] placeholders in the request body before it reaches the
AI provider. The request goes through normally with clean content;
the user gets a notification about what was redacted.

Modes:
  - "monitor": Log the violation, allow the request unchanged.
  - "warn":    Redact PII from request body, notify user, forward clean request.
  - "block":   Redact PII from request body, notify user, forward clean request.

Design principles:
  - Fail-open: Any exception during matching returns ("allow", None).
  - Thread-safe: All public methods are guarded by a lock.
  - Never return 403 -- always redact and forward.
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# =============================================================================
# FALLBACK PII PATTERNS -- used when Presidio is not available
# =============================================================================

FALLBACK_PII_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    ),
    # Phone: require structural separators (dashes, dots, spaces, parens) or
    # a leading +. Plain digit sequences like "1234567890" are NOT matched
    # to avoid false positives on IDs, timestamps, etc.
    "phone": re.compile(
        r"\+\d{1,3}[-.\s]\d{1,4}(?:[-.\s]\d{2,4}){1,3}\b"   # +1-555-123-4567, +44 20 7946 0958
        r"|\b\(?\d{3}\)[-.\s]\d{3}[-.\s]\d{4}\b"              # (555) 123-4567
        r"|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"                   # 555-123-4567, 555.123.4567
    ),
    "ssn": re.compile(
        r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"
    ),
    "credit_card": re.compile(
        r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
    ),
    "api_key": re.compile(
        r"\b(?:sk[-_]|api[-_]?key[-_]?|bearer\s+|token[-_]?)[a-zA-Z0-9]{16,}\b",
        re.IGNORECASE,
    ),
    "aws_key": re.compile(
        r"\bAKIA[0-9A-Z]{16}\b"
    ),
    "github_token": re.compile(
        r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b"
    ),
    "ip_address": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    ),
    "private_key": re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        re.IGNORECASE,
    ),
}


# =============================================================================
# PRESIDIO CONFIGURATION
# =============================================================================

# Map Presidio entity types to Oximy data type names
PRESIDIO_TO_OXIMY: dict[str, str] = {
    "CREDIT_CARD": "credit_card",
    "EMAIL_ADDRESS": "email",
    "PHONE_NUMBER": "phone",
    "US_SSN": "ssn",
    "IP_ADDRESS": "ip_address",
    "PERSON": "person_name",
    "LOCATION": "location",
    "API_KEY": "api_key",
    "AWS_KEY": "aws_key",
    "GITHUB_TOKEN": "github_token",
    "PRIVATE_KEY": "private_key",
}

# Reverse mapping: Oximy name -> Presidio entity type
OXIMY_TO_PRESIDIO: dict[str, str] = {v: k for k, v in PRESIDIO_TO_OXIMY.items()}

# Confidence thresholds per detection method
NER_ENTITY_TYPES = {"PERSON", "LOCATION"}
CUSTOM_ENTITY_TYPES = {"API_KEY", "AWS_KEY", "GITHUB_TOKEN", "PRIVATE_KEY"}

CONFIDENCE_THRESHOLDS: dict[str, float] = {}
# Pattern-based (built-in Presidio recognizers)
for _etype in ("CREDIT_CARD", "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "IP_ADDRESS"):
    CONFIDENCE_THRESHOLDS[_etype] = 0.5
# NER-based
for _etype in NER_ENTITY_TYPES:
    CONFIDENCE_THRESHOLDS[_etype] = 0.6
# Custom patterns
for _etype in CUSTOM_ENTITY_TYPES:
    CONFIDENCE_THRESHOLDS[_etype] = 0.7

# Body size threshold above which NER is skipped for performance
NER_SKIP_BODY_SIZE = 100_000  # 100 KB

# =============================================================================
# LAZY-LOADED PRESIDIO ENGINES
# =============================================================================

_analyzer_engine = None
_anonymizer_engine = None
_presidio_available: bool | None = None  # None = not yet checked


def _add_custom_recognizers(analyzer) -> None:
    """Register custom pattern recognizers for types Presidio lacks."""
    try:
        from presidio_analyzer import Pattern, PatternRecognizer
    except ImportError:
        return

    custom_recognizers = [
        PatternRecognizer(
            supported_entity="API_KEY",
            name="api_key_recognizer",
            patterns=[
                Pattern(
                    name="api_key_pattern",
                    regex=r"\b(?:sk[-_]|api[-_]?key[-_]?|bearer\s+|token[-_]?)[a-zA-Z0-9]{16,}\b",
                    score=0.8,
                ),
            ],
            supported_language="en",
        ),
        PatternRecognizer(
            supported_entity="AWS_KEY",
            name="aws_key_recognizer",
            patterns=[
                Pattern(
                    name="aws_key_pattern",
                    regex=r"\bAKIA[0-9A-Z]{16}\b",
                    score=0.95,
                ),
            ],
            supported_language="en",
        ),
        PatternRecognizer(
            supported_entity="GITHUB_TOKEN",
            name="github_token_recognizer",
            patterns=[
                Pattern(
                    name="github_token_pattern",
                    regex=r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b",
                    score=0.95,
                ),
            ],
            supported_language="en",
        ),
        PatternRecognizer(
            supported_entity="PRIVATE_KEY",
            name="private_key_recognizer",
            patterns=[
                Pattern(
                    name="private_key_pattern",
                    regex=r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
                    score=0.95,
                ),
            ],
            supported_language="en",
        ),
    ]

    for recognizer in custom_recognizers:
        analyzer.registry.add_recognizer(recognizer)


def _get_analyzer():
    """Lazy-load and return the Presidio AnalyzerEngine, or None if unavailable."""
    global _analyzer_engine, _presidio_available
    if _presidio_available is False:
        return None
    if _analyzer_engine is not None:
        return _analyzer_engine
    try:
        from presidio_analyzer import AnalyzerEngine
        _analyzer_engine = AnalyzerEngine()
        _add_custom_recognizers(_analyzer_engine)
        _presidio_available = True
        logger.info("Presidio AnalyzerEngine initialized successfully")
        return _analyzer_engine
    except ImportError:
        logger.warning("Presidio not available, falling back to regex patterns")
        _presidio_available = False
        return None
    except Exception:
        logger.warning("Failed to initialize Presidio, falling back to regex patterns", exc_info=True)
        _presidio_available = False
        return None


def _get_anonymizer():
    """Lazy-load and return the Presidio AnonymizerEngine, or None if unavailable."""
    global _anonymizer_engine
    if _presidio_available is False:
        return None
    if _anonymizer_engine is not None:
        return _anonymizer_engine
    try:
        from presidio_anonymizer import AnonymizerEngine
        _anonymizer_engine = AnonymizerEngine()
        return _anonymizer_engine
    except ImportError:
        return None
    except Exception:
        logger.warning("Failed to initialize Presidio AnonymizerEngine", exc_info=True)
        return None


def _get_redaction_operators() -> dict | None:
    """Build the operator config dict for Presidio anonymization."""
    try:
        from presidio_anonymizer.entities import OperatorConfig
    except ImportError:
        return None

    return {
        "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[CREDIT_CARD_REDACTED]"}),
        "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL_REDACTED]"}),
        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE_REDACTED]"}),
        "US_SSN": OperatorConfig("replace", {"new_value": "[SSN_REDACTED]"}),
        "IP_ADDRESS": OperatorConfig("replace", {"new_value": "[IP_ADDRESS_REDACTED]"}),
        "PERSON": OperatorConfig("replace", {"new_value": "[PERSON_REDACTED]"}),
        "LOCATION": OperatorConfig("replace", {"new_value": "[LOCATION_REDACTED]"}),
        "API_KEY": OperatorConfig("replace", {"new_value": "[API_KEY_REDACTED]"}),
        "AWS_KEY": OperatorConfig("replace", {"new_value": "[AWS_KEY_REDACTED]"}),
        "GITHUB_TOKEN": OperatorConfig("replace", {"new_value": "[GITHUB_TOKEN_REDACTED]"}),
        "PRIVATE_KEY": OperatorConfig("replace", {"new_value": "[PRIVATE_KEY_REDACTED]"}),
        "DEFAULT": OperatorConfig("replace", {"new_value": "[PII_REDACTED]"}),
    }


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class EnforcementRule:
    """A single detection rule within a policy.

    Attributes:
        id:         Unique rule identifier.
        type:       "data_type" (uses Presidio/regex) or "regex" (custom patterns).
        name:       Human-readable rule name.
        severity:   "low", "medium", "high", or "critical".
        patterns:   Pre-compiled custom regex patterns (for type="regex").
        data_types: PII type keys to check (for type="data_type").
    """

    id: str
    type: str
    name: str
    severity: str
    patterns: list[re.Pattern] = field(default_factory=list)
    data_types: list[str] = field(default_factory=list)


@dataclass
class EnforcementPolicy:
    """A named policy containing one or more rules.

    Attributes:
        id:    Unique policy identifier.
        name:  Human-readable policy name.
        mode:  Enforcement mode -- "warn", "block", or "monitor".
        rules: Ordered list of rules evaluated top-to-bottom.
    """

    id: str
    name: str
    mode: str
    rules: list[EnforcementRule] = field(default_factory=list)


@dataclass
class Violation:
    """Record of a detected PII violation.

    Attributes:
        id:             Unique violation identifier (v_{timestamp}_{hex}).
        timestamp:      ISO 8601 UTC timestamp of detection.
        action:         Action taken -- "blocked", "warned", or "redacted".
        policy_id:      ID of the policy that triggered.
        policy_name:    Name of the policy that triggered.
        rule_id:        ID of the rule that matched.
        rule_name:      Name of the rule that matched.
        rule_type:      Type of the matching rule ("data_type", "regex", "keyword").
        severity:       Severity level from the matching rule.
        detected_type:  PII type or pattern name that matched.
        host:           Request target host.
        path:           Request path.
        method:         HTTP method (GET, POST, etc.).
        bundle_id:      Client application bundle identifier.
        retry_allowed:  Whether a retry within the TTL window will pass.
        message:        Human-readable violation description.
    """

    id: str
    timestamp: str
    action: str
    policy_id: str
    policy_name: str
    rule_id: str
    rule_name: str
    rule_type: str
    severity: str
    detected_type: str
    host: str
    path: str
    method: str
    bundle_id: str
    retry_allowed: bool
    message: str


# =============================================================================
# ENFORCEMENT ENGINE
# =============================================================================


class EnforcementEngine:
    """PII detection and enforcement engine.

    Scans request bodies against configured policies and returns an action:
      - ("allow", None)      -- no violation found, or fail-open on error
      - ("allow", Violation)  -- violation found but policy mode is "monitor"
      - ("warn", Violation)   -- first occurrence blocked; retry allowed within TTL
      - ("block", Violation)  -- always blocked

    Uses Microsoft Presidio for PII detection when available, with automatic
    fallback to regex patterns. Presidio provides built-in Luhn validation
    for credit cards, NER-based detection for names/locations, and confidence
    scoring.

    Thread-safe. All public methods acquire ``self._lock``.

    Lifecycle::

        engine = EnforcementEngine()
        engine.update_policies(server_config)
        action, violation = engine.check_request(body, host, path, method, bundle_id)
    """

    MAX_BODY_SIZE: int = 1_048_576  # 1 MB -- skip scanning oversized bodies
    WARN_RETRY_TTL: int = 120       # 2 minutes -- warn cache time-to-live

    def __init__(self) -> None:
        self._policies: list[EnforcementPolicy] = []  # Empty until server provides policies
        # Warn cache: (host, path_prefix, rule_id) -> timestamp of first warn
        self._warn_cache: dict[tuple[str, str, str], float] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def update_policies(self, policies_data: list[dict]) -> None:
        """Load policies from server config, replacing defaults.

        Expects a list of dicts, each with keys:
            id, name, mode, rules (list of rule dicts)

        Rule dicts have keys:
            id, type, name, severity, patterns? (list[str]), data_types? (list[str])

        Custom regex patterns are pre-compiled at load time. Invalid patterns
        are logged and skipped.

        Args:
            policies_data: Raw policy dicts from the server configuration API.
        """
        parsed: list[EnforcementPolicy] = []

        for policy_dict in policies_data:
            rules: list[EnforcementRule] = []
            for rule_dict in policy_dict.get("rules", []):
                # Pre-compile custom regex patterns
                compiled_patterns: list[re.Pattern] = []
                for raw_pattern in rule_dict.get("patterns", []):
                    try:
                        compiled_patterns.append(re.compile(raw_pattern))
                    except re.error as exc:
                        logger.warning(
                            "Skipping invalid regex in rule %s: %s (%s)",
                            rule_dict.get("id", "?"),
                            raw_pattern,
                            exc,
                        )

                rules.append(
                    EnforcementRule(
                        id=rule_dict.get("id", ""),
                        type=rule_dict.get("type", "data_type"),
                        name=rule_dict.get("name", ""),
                        severity=rule_dict.get("severity", "medium"),
                        patterns=compiled_patterns,
                        data_types=rule_dict.get("dataTypes") or rule_dict.get("data_types", []),
                    )
                )

            parsed.append(
                EnforcementPolicy(
                    id=policy_dict.get("id", ""),
                    name=policy_dict.get("name", ""),
                    mode=policy_dict.get("mode", "warn"),
                    rules=rules,
                )
            )

        with self._lock:
            self._policies = parsed
            self._warn_cache.clear()


        logger.info(
            "Enforcement policies updated: %d policy(ies) loaded",
            len(self._policies),
        )

    # ------------------------------------------------------------------
    # Request checking
    # ------------------------------------------------------------------

    def check_request(
        self,
        body_text: str,
        host: str,
        path: str,
        method: str,
        bundle_id: str = "",
    ) -> tuple[str, Violation | None]:
        """Check a request body for PII violations.

        Scans ``body_text`` against all active policies and rules.

        Returns:
            A tuple of (action, violation):
              - ("allow", None)       -- clean, no match
              - ("allow", Violation)  -- match but mode is "monitor"
              - ("allow", None)       -- match but warn cache allows retry
              - ("warn", Violation)   -- first warn, request blocked
              - ("block", Violation)  -- always blocked

        Fail-open: returns ("allow", None) on any internal exception.
        """
        try:
            return self._check_request_inner(
                body_text, host, path, method, bundle_id
            )
        except Exception:
            logger.debug(
                "Enforcement check failed (fail-open) for %s %s",
                method,
                host + path,
                exc_info=True,
            )
            return ("allow", None)

    def _check_request_inner(
        self,
        body_text: str,
        host: str,
        path: str,
        method: str,
        bundle_id: str,
    ) -> tuple[str, Violation | None]:
        """Core matching logic -- called inside the fail-open wrapper."""
        # Skip oversized bodies
        if len(body_text) > self.MAX_BODY_SIZE:
            return ("allow", None)

        with self._lock:
            policies = list(self._policies)

        # Clean expired warn cache entries opportunistically
        self._clean_warn_cache()

        for policy in policies:
            for rule in policy.rules:
                detected_type = self._match_rule(rule, body_text)
                if detected_type is None:
                    continue

                # Build violation record
                now = time.time()
                violation = Violation(
                    id=f"v_{int(now)}_{uuid.uuid4().hex[:8]}",
                    timestamp=datetime.fromtimestamp(
                        now, tz=timezone.utc
                    ).isoformat(),
                    action="blocked" if policy.mode == "block" else "warned",
                    policy_id=policy.id,
                    policy_name=policy.name,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    rule_type=rule.type,
                    severity=rule.severity,
                    detected_type=detected_type,
                    host=host,
                    path=path,
                    method=method,
                    bundle_id=bundle_id,
                    retry_allowed=(policy.mode == "warn"),
                    message=(
                        f"Detected {detected_type} in {method} {host}{path} "
                        f"[{policy.name} / {rule.name}]"
                    ),
                )

                # Apply policy mode
                if policy.mode == "monitor":
                    return ("allow", violation)

                if policy.mode == "block":
                    return ("block", violation)

                # mode == "warn": check the retry cache
                path_prefix = self._get_path_prefix(path)
                cache_key = (host, path_prefix, rule.id)

                with self._lock:
                    cached_ts = self._warn_cache.get(cache_key)
                    if cached_ts is not None:
                        elapsed = now - cached_ts
                        if elapsed < self.WARN_RETRY_TTL:
                            # Within TTL -- allow the retry
                            return ("allow", None)
                        # TTL expired -- treat as new first occurrence
                    # Record first occurrence
                    self._warn_cache[cache_key] = now

                return ("warn", violation)

        return ("allow", None)

    # ------------------------------------------------------------------
    # Pattern matching
    # ------------------------------------------------------------------

    @staticmethod
    def _match_rule(rule: EnforcementRule, body: str) -> str | None:
        """Check body against a single rule.

        Uses Presidio when available for data_type rules, falling back to
        regex patterns. For custom regex rules, always uses direct matching.

        Returns the name of the first matched PII type / pattern,
        or None if nothing matched.
        """
        if rule.type == "data_type":
            return EnforcementEngine._match_data_types(rule.data_types, body)
        elif rule.type == "regex":
            for idx, pattern in enumerate(rule.patterns):
                if pattern.search(body):
                    return f"custom_pattern_{idx}"
        return None

    @staticmethod
    def _match_data_types(data_types: list[str], body: str) -> str | None:
        """Match data types using Presidio or fallback regex.

        For large bodies (>100KB), skips NER-based detection (PERSON, LOCATION)
        to keep latency under 50ms.
        """
        analyzer = _get_analyzer()
        if analyzer is None:
            # Fallback: use regex patterns
            return EnforcementEngine._match_data_types_regex(data_types, body)

        try:
            return EnforcementEngine._match_data_types_presidio(
                analyzer, data_types, body
            )
        except Exception:
            logger.debug(
                "Presidio analysis failed, falling back to regex", exc_info=True
            )
            return EnforcementEngine._match_data_types_regex(data_types, body)

    @staticmethod
    def _match_data_types_presidio(
        analyzer, data_types: list[str], body: str
    ) -> str | None:
        """Use Presidio to detect PII types in body text."""
        # Determine which Presidio entity types to request
        requested_entities: list[str] = []
        skip_ner = len(body) > NER_SKIP_BODY_SIZE

        for dt in data_types:
            presidio_type = OXIMY_TO_PRESIDIO.get(dt)
            if presidio_type is None:
                continue
            if skip_ner and presidio_type in NER_ENTITY_TYPES:
                continue
            requested_entities.append(presidio_type)

        if not requested_entities:
            return None

        results = analyzer.analyze(
            text=body,
            entities=requested_entities,
            language="en",
        )

        # Check results against confidence thresholds
        for result in results:
            threshold = CONFIDENCE_THRESHOLDS.get(result.entity_type, 0.5)
            if result.score >= threshold:
                oximy_type = PRESIDIO_TO_OXIMY.get(result.entity_type)
                if oximy_type and oximy_type in data_types:
                    return oximy_type

        return None

    @staticmethod
    def _match_data_types_regex(data_types: list[str], body: str) -> str | None:
        """Fallback regex-based PII matching."""
        for dt in data_types:
            pattern = FALLBACK_PII_PATTERNS.get(dt)
            if pattern and pattern.search(body):
                return dt
        return None

    # ------------------------------------------------------------------
    # Warn cache management
    # ------------------------------------------------------------------

    def _clean_warn_cache(self) -> None:
        """Remove expired entries from the warn cache."""
        now = time.time()
        with self._lock:
            expired = [
                key
                for key, ts in self._warn_cache.items()
                if now - ts >= self.WARN_RETRY_TTL
            ]
            for key in expired:
                del self._warn_cache[key]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_path_prefix(path: str) -> str:
        """Get the first two segments of a URL path for cache keying.

        Examples:
            "/v1/chat/completions"       -> "/v1/chat"
            "/api/v2/users/123/profile"  -> "/api/v2"
            "/health"                    -> "/health"
            "/"                          -> "/"
        """
        segments = [s for s in path.split("/") if s]
        if len(segments) <= 2:
            return "/" + "/".join(segments) if segments else "/"
        return "/" + "/".join(segments[:2])

    # ------------------------------------------------------------------
    # PII Redaction
    # ------------------------------------------------------------------

    # Labels used in redaction placeholders per PII type
    _REDACT_LABELS: dict[str, str] = {
        "email": "EMAIL",
        "phone": "PHONE",
        "ssn": "SSN",
        "credit_card": "CREDIT_CARD",
        "api_key": "API_KEY",
        "aws_key": "AWS_KEY",
        "github_token": "GITHUB_TOKEN",
        "ip_address": "IP_ADDRESS",
        "private_key": "PRIVATE_KEY",
        "person_name": "PERSON",
        "location": "LOCATION",
    }

    def redact_pii(self, body_text: str) -> tuple[str, list[str]]:
        """Replace all detected PII in *body_text* with [REDACTED] placeholders.

        Uses Presidio AnonymizerEngine when available for accurate redaction
        with entity-specific replacement labels. Falls back to regex-based
        substitution.

        Returns:
            (redacted_body, list_of_detected_types)
            If no PII is found, returns (body_text, []).
        """
        try:
            return self._redact_pii_inner(body_text)
        except Exception:
            logger.debug("PII redaction failed (fail-open)", exc_info=True)
            return (body_text, [])

    def _redact_pii_inner(self, body_text: str) -> tuple[str, list[str]]:
        if len(body_text) > self.MAX_BODY_SIZE:
            return (body_text, [])

        with self._lock:
            policies = list(self._policies)

        # Gather all data_types to check from active rules
        data_types_to_check: set[str] = set()
        for policy in policies:
            if policy.mode == "monitor":
                continue
            for rule in policy.rules:
                if rule.type == "data_type":
                    data_types_to_check.update(rule.data_types)

        if not data_types_to_check:
            return (body_text, [])

        # Try Presidio-based redaction first
        analyzer = _get_analyzer()
        anonymizer = _get_anonymizer()

        if analyzer is not None and anonymizer is not None:
            try:
                return self._redact_pii_presidio(
                    analyzer, anonymizer, body_text, data_types_to_check
                )
            except Exception:
                logger.debug(
                    "Presidio redaction failed, falling back to regex",
                    exc_info=True,
                )

        # Fallback: regex-based redaction
        return self._redact_pii_regex(body_text, data_types_to_check)

    def _redact_pii_presidio(
        self,
        analyzer,
        anonymizer,
        body_text: str,
        data_types_to_check: set[str],
    ) -> tuple[str, list[str]]:
        """Use Presidio to analyze and anonymize PII in body text."""
        # Build list of Presidio entity types to request
        requested_entities: list[str] = []
        skip_ner = len(body_text) > NER_SKIP_BODY_SIZE

        for dt in data_types_to_check:
            presidio_type = OXIMY_TO_PRESIDIO.get(dt)
            if presidio_type is None:
                continue
            if skip_ner and presidio_type in NER_ENTITY_TYPES:
                continue
            requested_entities.append(presidio_type)

        if not requested_entities:
            return (body_text, [])

        # Analyze
        results = analyzer.analyze(
            text=body_text,
            entities=requested_entities,
            language="en",
        )

        # Filter by confidence threshold and only keep types we care about
        filtered_results = []
        detected_oximy_types: set[str] = set()

        for result in results:
            threshold = CONFIDENCE_THRESHOLDS.get(result.entity_type, 0.5)
            if result.score < threshold:
                continue
            oximy_type = PRESIDIO_TO_OXIMY.get(result.entity_type)
            if oximy_type and oximy_type in data_types_to_check:
                filtered_results.append(result)
                detected_oximy_types.add(oximy_type)

        if not filtered_results:
            return (body_text, [])

        # Anonymize using operator configs
        operators = _get_redaction_operators()
        anonymized = anonymizer.anonymize(
            text=body_text,
            analyzer_results=filtered_results,
            operators=operators,
        )

        return (anonymized.text, sorted(detected_oximy_types))

    def _redact_pii_regex(
        self, body_text: str, data_types_to_check: set[str]
    ) -> tuple[str, list[str]]:
        """Fallback regex-based PII redaction."""
        detected: list[str] = []
        redacted = body_text

        for dt in data_types_to_check:
            pattern = FALLBACK_PII_PATTERNS.get(dt)
            if not pattern:
                continue
            if pattern.search(redacted):
                label = self._REDACT_LABELS.get(dt, dt.upper())
                redacted = pattern.sub(f"[{label}_REDACTED]", redacted)
                detected.append(dt)

        return (redacted, detected)
