"""
Prompt injection heuristics for EiPL submissions.

Detects common injection patterns per OWASP LLM01:2025 guidance.
Flags suspicious input for logging — does NOT block most patterns
to avoid false positives on legitimate code descriptions.
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Patterns that indicate injection attempts. Each is (compiled_regex, category).
# These are intentionally conservative — better to miss a clever attack
# than to block a student writing "the function ignores the previous value".
_INJECTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Direct instruction overrides
    (
        re.compile(
            r"ignore\s+(all\s+)?(previous|above|prior|system)\s+(instructions?|prompts?|rules?)",
            re.I,
        ),
        "instruction_override",
    ),
    (
        re.compile(r"disregard\s+(all\s+)?(previous|above|prior)", re.I),
        "instruction_override",
    ),
    # Role manipulation
    (re.compile(r"you\s+are\s+(now|no\s+longer)\s", re.I), "role_manipulation"),
    (re.compile(r"pretend\s+(you|to\s+be)", re.I), "role_manipulation"),
    # Extraction attempts (most critical for segmentation service)
    (
        re.compile(
            r"(reveal|show|print|output|repeat|echo)\s+(the\s+)?(system|reference|original)\s+(prompt|code|solution|instructions?)",
            re.I,
        ),
        "extraction_attempt",
    ),
    # Code block injection
    (re.compile(r"```"), "code_fence"),
]


@dataclass
class InjectionAnalysis:
    """Result of prompt injection heuristic analysis."""

    flagged: bool
    flags: list[tuple[str, str]]  # (category, matched_text)
    risk_score: int  # 0-10


class PromptSanitizer:
    """
    Prompt injection detection for EiPL inputs.

    Follows project convention: @classmethod service, no DB dependencies.
    See AnonymizationService in purplex/utils/anonymization.py for pattern.
    """

    @classmethod
    def analyze(cls, text: str) -> InjectionAnalysis:
        """
        Analyze text for injection patterns.

        Returns InjectionAnalysis with flags and risk score.
        Does NOT modify the input text.
        """
        flags = []
        for pattern, category in _INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                flags.append((category, match.group()))

        risk_score = min(len(flags) * 3, 10)

        if flags:
            logger.warning(
                "EiPL injection heuristic triggered: "
                "flags=%s, risk_score=%d, input_preview=%.80r",
                [f[0] for f in flags],
                risk_score,
                text,
            )

        return InjectionAnalysis(
            flagged=len(flags) > 0,
            flags=flags,
            risk_score=risk_score,
        )
