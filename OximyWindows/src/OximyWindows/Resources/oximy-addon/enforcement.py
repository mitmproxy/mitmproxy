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
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone

logger = logging.getLogger(__name__)

# =============================================================================
# FALLBACK PII PATTERNS -- used when Presidio is not available
# =============================================================================

FALLBACK_PII_PATTERNS: dict[str, re.Pattern] = {
    # These are basic regex patterns for when Presidio is unavailable.
    # They only cover types that regex can reliably detect (structured formats).
    # NER-based types (person_name, location) require Presidio and are NOT
    # covered here — regex cannot generalize across languages/formats.
    "email": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    ),
    # Phone: only formatted numbers with separators to avoid false positives.
    # Bare digit sequences are handled by Presidio's phonenumbers library.
    "phone": re.compile(
        r"\+\d{1,3}[-.\s]\d{1,4}(?:[-.\s]\d{2,4}){1,3}\b"    # +1-555-123-4567, +44 20 7946 0958
        r"|\b\(?\d{3}\)[-.\s]\d{3}[-.\s]\d{4}\b"               # (555) 123-4567
        r"|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",                   # 555-123-4567, 555.123.4567
    ),
    # SSN: require separators to avoid false positives on protobuf/numeric IDs.
    "ssn": re.compile(
        r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b"
    ),
    # Credit card: require separators to avoid false positives.
    "credit_card": re.compile(
        r"\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b"
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
    # US Government IDs
    "US_DRIVER_LICENSE": "us_driver_license",
    "US_PASSPORT": "us_passport",
    "US_BANK_NUMBER": "us_bank_number",
    "US_ITIN": "us_itin",
    # International
    "IBAN_CODE": "iban_code",
    "UK_NHS": "uk_nhs",
    "SG_NRIC_FIN": "sg_nric",
    "IN_PAN": "in_pan",
    "AU_ABN": "au_abn",
    "AU_ACN": "au_acn",
    "AU_TFN": "au_tfn",
    # Medical
    "MEDICAL_LICENSE": "medical_license",
    # Network
    "URL": "url",
    "DOMAIN_NAME": "domain_name",
    # NER-based (detected via ML model)
    "ORGANIZATION": "organization",
    "DATE_TIME": "date_time",
    "NRP": "nationality",
}

# Reverse mapping: Oximy name -> Presidio entity type
OXIMY_TO_PRESIDIO: dict[str, str] = {v: k for k, v in PRESIDIO_TO_OXIMY.items()}

# Confidence thresholds per detection method
NER_ENTITY_TYPES = {"PERSON", "LOCATION", "ORGANIZATION", "DATE_TIME", "NRP"}
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
# Additional pattern-based types
for _etype in ("US_DRIVER_LICENSE", "US_PASSPORT", "US_BANK_NUMBER", "US_ITIN",
               "IBAN_CODE", "UK_NHS", "SG_NRIC_FIN", "IN_PAN", "AU_ABN", "AU_ACN", "AU_TFN",
               "MEDICAL_LICENSE", "URL", "DOMAIN_NAME"):
    CONFIDENCE_THRESHOLDS[_etype] = 0.5
# ORGANIZATION, DATE_TIME, NRP already get 0.6 from the NER_ENTITY_TYPES loop above

# Body size threshold above which NER is skipped for performance
NER_SKIP_BODY_SIZE = 100_000  # 100 KB

# Pattern to detect file/directory paths in text
# Matches Unix paths (/Users/john/...) and Windows paths (C:\Users\john\...)
_FILE_PATH_RE = re.compile(
    r'(?:[A-Za-z]:)?[/\\](?:[\w.@:~+-]+[/\\])+[\w.@:~+-]*'
)

# =============================================================================
# LAZY-LOADED PRESIDIO ENGINES
# =============================================================================

_analyzer_engine = None
_anonymizer_engine = None
_presidio_available: bool | None = None  # None = not yet checked


def _add_custom_recognizers(analyzer) -> None:
    """Register custom pattern recognizers for types Presidio lacks."""
    try:
        from presidio_analyzer import Pattern
        from presidio_analyzer import PatternRecognizer
    except ImportError:
        return

    custom_recognizers = [
        # -- Secrets / credentials --
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
        from presidio_analyzer.nlp_engine import NlpEngineProvider

        # Use en_core_web_md (~40MB) for NER (person, location, org, phone, etc.).
        # The md model includes word vectors for good accuracy at a fraction of
        # the size of en_core_web_lg (~560MB).
        nlp_config = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_md"}],
        }
        nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()
        _analyzer_engine = AnalyzerEngine(nlp_engine=nlp_engine)
        _add_custom_recognizers(_analyzer_engine)
        _presidio_available = True
        logger.info("Presidio AnalyzerEngine initialized with en_core_web_md")
        return _analyzer_engine
    except ImportError as exc:
        logger.warning("Presidio not available, falling back to regex patterns: %s", exc)
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
        id:               Unique violation identifier (v_{timestamp}_{hex}).
        timestamp:        ISO 8601 UTC timestamp of detection.
        action:           Action taken -- "blocked", "warned", or "redacted".
        policy_id:        ID of the policy that triggered.
        policy_name:      Name of the policy that triggered.
        rule_id:          ID of the rule that matched.
        rule_name:        Name of the rule that matched.
        rule_type:        Type of the matching rule ("data_type", "regex", "keyword").
        severity:         Severity level from the matching rule.
        detected_type:    PII type or pattern name that matched.
        host:             Request target host.
        path:             Request path.
        method:           HTTP method (GET, POST, etc.).
        bundle_id:        Client application bundle identifier.
        retry_allowed:    Whether a retry within the TTL window will pass.
        message:          Human-readable violation description.
        detection_method: Detection mechanism used; one of: presidio_ner,
                          presidio_pattern, presidio_custom, fallback_regex,
                          keyword, regex, ai_enforcement.
        confidence_score: Presidio confidence score (0-1); 1.0 for
                          regex/keyword matches.
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
    detection_method: str = ""
    confidence_score: float = 0.0


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
    # Pre-loading
    # ------------------------------------------------------------------

    def preload(self) -> None:
        """Eagerly load the Presidio AnalyzerEngine and spaCy model.

        On first launch of a newly installed app, macOS Gatekeeper verifies
        code signatures of native libraries (.so/.dylib) via OCSP/notarization
        checks.  Presidio + spaCy pull in numpy, thinc, cymem, preshed, blis,
        etc. — each with native extensions.  If these imports happen
        synchronously in the asyncio event loop (via the lazy ``_get_analyzer``
        call during enforcement), the event loop blocks for the duration of the
        Gatekeeper scan, freezing all traffic.

        Call this from a **background thread** during startup so that:
          - The GIL is released during dlopen() → event loop keeps running.
          - Gatekeeper verification completes before any enforcement check.
          - On second launch the imports are cached and nearly instant.
        """
        try:
            _get_analyzer()
        except Exception:
            logger.warning(
                "Presidio pre-load failed (will retry on first enforcement call)",
                exc_info=True,
            )

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
                            "Skipping invalid regex pattern in enforcement rule: %s",
                            exc,
                        )

                data_types = rule_dict.get("dataTypes") or rule_dict.get("data_types", [])

                # Warn about unrecognized data_type names (likely misconfigured)
                for dt in data_types:
                    if dt not in OXIMY_TO_PRESIDIO:
                        logger.warning(
                            "Unrecognized data_type in enforcement rule — "
                            "will be skipped during detection. "
                            "Valid types: %s",
                            ", ".join(sorted(OXIMY_TO_PRESIDIO.keys())),
                        )

                rules.append(
                    EnforcementRule(
                        id=rule_dict.get("id", ""),
                        type=rule_dict.get("type", "data_type"),
                        name=rule_dict.get("name", ""),
                        severity=rule_dict.get("severity", "medium"),
                        patterns=compiled_patterns,
                        data_types=data_types,
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
            # Clean expired warn-cache entries while we already hold the lock,
            # avoiding a separate lock acquisition (and the race it creates).
            _now_clean = time.time()
            _expired = [
                k for k, ts in self._warn_cache.items()
                if _now_clean - ts >= self.WARN_RETRY_TTL
            ]
            for k in _expired:
                del self._warn_cache[k]

        for policy in policies:
            for rule in policy.rules:
                match_result = self._match_rule(rule, body_text)
                if match_result is None:
                    continue

                detected_type, detection_method, confidence_score = match_result

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
                    detection_method=detection_method,
                    confidence_score=confidence_score,
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
    def _is_inside_file_path(result, body: str) -> bool:
        """Return True if a Presidio NER result overlaps with a file/directory path."""
        for m in _FILE_PATH_RE.finditer(body):
            if m.start() <= result.start and result.end <= m.end():
                return True
        return False

    @staticmethod
    def _match_rule(rule: EnforcementRule, body: str) -> tuple[str, str, float] | None:
        """Check body against a single rule.

        Uses Presidio when available for data_type rules, falling back to
        regex patterns. For custom regex rules, always uses direct matching.

        Returns a tuple of (detected_type, detection_method, confidence_score)
        for the first match, or None if nothing matched.  detection_method is
        one of: "presidio_ner", "presidio_pattern", "presidio_custom",
        "fallback_regex", "keyword", "regex".
        """
        if rule.type == "data_type":
            return EnforcementEngine._match_data_types(rule.data_types, body)
        elif rule.type in ("regex", "keyword"):
            for idx, pattern in enumerate(rule.patterns):
                if pattern.search(body):
                    return (f"custom_pattern_{idx}", rule.type, 1.0)
        return None

    @staticmethod
    def _match_data_types(data_types: list[str], body: str) -> tuple[str, str, float] | None:
        """Match data types using Presidio or fallback regex.

        For large bodies (>100KB), skips NER-based detection (PERSON, LOCATION)
        to keep latency under 50ms.

        Defense in depth: if Presidio is available but returns no match,
        we still try the regex patterns as a safety net.  This covers gaps
        where Presidio's recognizers under-detect (e.g. US_SSN patterns or
        PHONE_NUMBER confidence below threshold).

        Returns:
            A tuple of (oximy_type, detection_method, confidence_score) on
            match, or None if nothing matched.
        """
        analyzer = _get_analyzer()
        if analyzer is None:
            # Fallback: use regex patterns
            return EnforcementEngine._match_data_types_regex(data_types, body)

        try:
            result = EnforcementEngine._match_data_types_presidio(
                analyzer, data_types, body
            )
            if result is not None:
                return result
            # Presidio found nothing — try regex as safety net
            return EnforcementEngine._match_data_types_regex(data_types, body)
        except Exception:
            logger.debug(
                "Presidio analysis failed, falling back to regex", exc_info=True
            )
            return EnforcementEngine._match_data_types_regex(data_types, body)

    @staticmethod
    def _match_data_types_presidio(
        analyzer, data_types: list[str], body: str
    ) -> tuple[str, str, float] | None:
        """Use Presidio to detect PII types in body text.

        Returns:
            A tuple of (oximy_type, detection_method, confidence_score) for the
            first match, or None if nothing matched.  detection_method is one of:
            "presidio_ner", "presidio_custom", or "presidio_pattern".
        """
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
                # Skip ANY entity type that falls inside a file/directory path
                if EnforcementEngine._is_inside_file_path(result, body):
                    continue
                oximy_type = PRESIDIO_TO_OXIMY.get(result.entity_type)
                if oximy_type and oximy_type in data_types:
                    # Determine detection sub-method
                    if result.entity_type in NER_ENTITY_TYPES:
                        method = "presidio_ner"
                    elif result.entity_type in CUSTOM_ENTITY_TYPES:
                        method = "presidio_custom"
                    else:
                        method = "presidio_pattern"
                    return (oximy_type, method, result.score)

        return None

    @staticmethod
    def _match_data_types_regex(data_types: list[str], body: str) -> tuple[str, str, float] | None:
        """Fallback regex-based PII matching.

        Returns:
            A tuple of (oximy_type, "fallback_regex", 1.0) for the first match,
            or None if nothing matched.
        """
        for dt in data_types:
            pattern = FALLBACK_PII_PATTERNS.get(dt)
            if pattern and pattern.search(body):
                return (dt, "fallback_regex", 1.0)
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
        "us_driver_license": "DRIVER_LICENSE",
        "us_passport": "PASSPORT",
        "iban_code": "IBAN",
        "us_bank_number": "BANK_ACCOUNT",
        "us_itin": "ITIN",
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

        # Gather data_types and custom regex/keyword patterns from active rules
        data_types_to_check: set[str] = set()
        custom_patterns: list[tuple[re.Pattern, str]] = []  # (pattern, label)
        for policy in policies:
            if policy.mode == "monitor":
                continue
            for rule in policy.rules:
                if rule.type == "data_type":
                    data_types_to_check.update(rule.data_types)
                elif rule.type in ("regex", "keyword"):
                    for idx, pattern in enumerate(rule.patterns):
                        label = rule.name or f"custom_pattern_{idx}"
                        custom_patterns.append((pattern, label))

        if not data_types_to_check and not custom_patterns:
            return (body_text, [])

        redacted_text = body_text
        detected_types: list[str] = []

        # Redact custom regex/keyword patterns first
        for pattern, label in custom_patterns:
            new_text, count = pattern.subn("[CUSTOM_REDACTED]", redacted_text)
            if count > 0:
                redacted_text = new_text
                detected_types.append(label)

        # Redact data_type rules via Presidio (or regex fallback)
        if data_types_to_check:
            analyzer = _get_analyzer()
            anonymizer = _get_anonymizer()

            if analyzer is not None and anonymizer is not None:
                try:
                    presidio_text, presidio_types = self._redact_pii_presidio(
                        analyzer, anonymizer, redacted_text, data_types_to_check
                    )
                    redacted_text = presidio_text
                    detected_types.extend(presidio_types)
                    # Safety net: run regex on types Presidio didn't catch
                    remaining = data_types_to_check - set(presidio_types)
                    if remaining:
                        regex_text, regex_types = self._redact_pii_regex(
                            redacted_text, remaining
                        )
                        redacted_text = regex_text
                        detected_types.extend(regex_types)
                except Exception:
                    logger.debug(
                        "Presidio redaction failed, falling back to regex",
                        exc_info=True,
                    )
                    regex_text, regex_types = self._redact_pii_regex(
                        redacted_text, data_types_to_check
                    )
                    redacted_text = regex_text
                    detected_types.extend(regex_types)
            else:
                regex_text, regex_types = self._redact_pii_regex(
                    redacted_text, data_types_to_check
                )
                redacted_text = regex_text
                detected_types.extend(regex_types)

        return (redacted_text, detected_types)

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
            # Skip entities inside file paths
            if EnforcementEngine._is_inside_file_path(result, body_text):
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
