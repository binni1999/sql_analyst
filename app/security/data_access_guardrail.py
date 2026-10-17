"""Policy checks for requests that could expose secrets or bulk personal data.

This is a conservative application-layer gate. It runs before graph/LLM/SQL
execution; it is not a replacement for database roles, row-level authorization,
or column-level masking.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DataAccessPolicyResult:
    allowed: bool
    reason: str | None = None
    rules: list[str] = field(default_factory=list)


class DataAccessGuardrail:
    """Reject explicit secret-exfiltration and bulk customer-record requests."""

    _DATA_ACTION = re.compile(
        r"\b(?:show|display|list|give|return|fetch|retrieve|export|dump|print|reveal|"
        r"select|get|provide)\b",
        re.IGNORECASE,
    )
    _SECRET = re.compile(
        r"\b(?:private\s+credentials?|credentials?|passwords?|password hashes|"
        r"api keys?|access tokens?|refresh tokens?|secret keys?|private keys?|"
        r"database credentials?|connection strings?|authentication secrets?)\b",
        re.IGNORECASE,
    )
    _CUSTOMER_RECORDS = re.compile(
        r"\b(?:all\s+)?customer\s+(?:records|profiles|details|personal data|information)\b|"
        r"\b(?:records|details|personal data|information)\s+for\s+(?:all\s+)?customers\b",
        re.IGNORECASE,
    )
    _BULK_PII = re.compile(
        r"\b(?:email addresses?|phone numbers?|home addresses?|dates? of birth|"
        r"government ids?|social security numbers?)\b",
        re.IGNORECASE,
    )

    def validate(self, question: str) -> DataAccessPolicyResult:
        text = re.sub(r"\s+", " ", question or "").strip()
        action = bool(self._DATA_ACTION.search(text))
        secret_request = action and bool(self._SECRET.search(text))
        customer_record_request = action and bool(self._CUSTOMER_RECORDS.search(text))
        bulk_pii_request = action and bool(self._BULK_PII.search(text)) and bool(
            re.search(r"\b(?:all|every|any|customer|customers|users|user records)\b", text, re.I)
        )

        rules: list[str] = []
        if secret_request:
            rules.append("secret_disclosure")
        if customer_record_request or bulk_pii_request:
            rules.append("bulk_personal_data")

        if rules:
            return DataAccessPolicyResult(
                allowed=False,
                reason=(
                    "This request could disclose credentials or sensitive customer data. "
                    "DataPilot cannot return secrets or bulk customer records without "
                    "an explicit authorization policy. Ask an authorized administrator "
                    "for access to an approved, narrowly scoped dataset."
                ),
                rules=rules,
            )
        return DataAccessPolicyResult(allowed=True)
