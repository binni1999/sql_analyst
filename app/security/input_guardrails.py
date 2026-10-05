from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .models import GuardrailViolation


@dataclass(frozen=True)
class PromptSecurityPolicy:
    """Policy for high-confidence prompt-injection detection at input time."""

    enabled: bool = True
    max_input_length: int = 1000
    block_prompt_extraction: bool = True
    block_instruction_override: bool = True
    block_tool_manipulation: bool = True
    block_security_bypass: bool = True
    minimum_matches_for_block: int = 1

    def __post_init__(self) -> None:
        if self.max_input_length <= 0:
            raise ValueError("max_input_length must be greater than zero")
        if self.minimum_matches_for_block <= 0:
            raise ValueError("minimum_matches_for_block must be greater than zero")


@dataclass(frozen=True)
class PromptSecurityResult:
    allowed: bool
    violations: list[GuardrailViolation] = field(default_factory=list)
    normalized_input: str | None = None


class PromptInjectionGuardrail:
    """Detect high-confidence attempts to manipulate the agent instructions.

    This is an input-layer defense only. It never replaces SQL parsing,
    authorization, complexity checks, or the secure database executor.
    """

    _RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
        (
            "prompt_extraction",
            "Prompt extraction attempts are not permitted.",
            (
                r"\b(?:reveal|show|print|display|output|give)\b.{0,80}\b(?:system|developer|hidden)\b.{0,40}\b(?:prompt|instructions)\b",
                r"\b(?:what|tell me)\b.{0,60}\b(?:system|developer)\b.{0,40}\b(?:prompt|instructions)\b",
            ),
        ),
        (
            "instruction_override",
            "Attempts to override or replace agent instructions are not permitted.",
            (
                r"\bignore\b.{0,80}\b(?:previous|prior|above|system|developer)\b.{0,40}\b(?:instructions?|rules?|constraints?)\b",
                r"\b(?:forget|disregard|override|bypass|replace)\b.{0,60}\b(?:previous|prior|system|developer|safety|security)\b",
                r"\b(?:new|updated)\s+(?:system|developer)\s+(?:prompt|instructions?)\b",
            ),
        ),
        (
            "tool_manipulation",
            "Attempts to manipulate agent tools or tool execution are not permitted.",
            (
                r"\b(?:call|invoke|execute|use)\b.{0,60}\b(?:tool|function)\b.{0,80}\b(?:without|ignore|skip|bypass)\b.{0,50}\b(?:validation|approval|security|guardrail)\b",
                r"\b(?:run|execute)\b.{0,80}\b(?:sql|query)\b.{0,80}\b(?:without|bypass|skip)\b.{0,50}\b(?:validation|guardrail|authorization)\b",
            ),
        ),
        (
            "security_bypass",
            "Attempts to bypass SQL security controls are not permitted.",
            (
                r"\b(?:disable|bypass|skip|turn\s+off|ignore)\b.{0,80}\b(?:security|guardrail|authorization|read[- ]only|row\s+limit|query\s+limit|timeout)\b",
                r"\b(?:allow|permit)\b.{0,80}\b(?:insert|update|delete|drop|alter|truncate)\b.{0,60}\b(?:anyway|regardless|ignore|bypass)\b",
            ),
        ),
    )

    def __init__(self, policy: PromptSecurityPolicy | None = None) -> None:
        self.policy = policy or PromptSecurityPolicy()

    def validate(self, text: str) -> PromptSecurityResult:
        if not self.policy.enabled:
            return PromptSecurityResult(allowed=True, normalized_input=text)

        normalized = self.normalize(text)
        violations: list[GuardrailViolation] = []

        if len(normalized) > self.policy.max_input_length:
            violations.append(
                GuardrailViolation(
                    rule="input_length",
                    message=(
                        "Input exceeds the configured prompt-security maximum "
                        f"of {self.policy.max_input_length} characters."
                    ),
                )
            )
            return PromptSecurityResult(False, violations, normalized)

        rule_enabled = {
            "prompt_extraction": self.policy.block_prompt_extraction,
            "instruction_override": self.policy.block_instruction_override,
            "tool_manipulation": self.policy.block_tool_manipulation,
            "security_bypass": self.policy.block_security_bypass,
        }

        matches = 0
        for rule, message, patterns in self._RULES:
            if not rule_enabled[rule]:
                continue
            if any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in patterns):
                matches += 1
                violations.append(
                    GuardrailViolation(rule=rule, message=message)
                )

        if matches < self.policy.minimum_matches_for_block:
            return PromptSecurityResult(True, [], normalized)

        return PromptSecurityResult(False, violations, normalized)

    @staticmethod
    def normalize(text: str) -> str:
        if not isinstance(text, str):
            return ""
        value = unicodedata.normalize("NFKC", text)
        value = value.replace("\u200b", "").replace("\ufeff", "")
        value = re.sub(r"\s+", " ", value).strip()
        return value
