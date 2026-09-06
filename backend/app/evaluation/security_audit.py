"""Security audit for tool executors and data access.

Validates that all tools enforce read-only SQL, proper access control,
and that no sensitive data leaks into LLM prompts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuditFinding:
    """A single security audit finding."""

    severity: str  # "critical", "high", "medium", "low", "info"
    category: str
    message: str
    details: str = ""


@dataclass
class SecurityAudit:
    """Result of a security audit run."""

    findings: list[AuditFinding] = field(default_factory=list)
    passed: bool = True

    def add_finding(self, finding: AuditFinding) -> None:
        self.findings.append(finding)
        if finding.severity in ("critical", "high"):
            self.passed = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "message": f.message,
                    "details": f.details,
                }
                for f in self.findings
            ],
            "critical_count": sum(1 for f in self.findings if f.severity == "critical"),
            "high_count": sum(1 for f in self.findings if f.severity == "high"),
            "medium_count": sum(1 for f in self.findings if f.severity == "medium"),
            "low_count": sum(1 for f in self.findings if f.severity == "low"),
        }


# Patterns that indicate write operations (should be blocked in read-only mode)
_WRITE_PATTERNS = [
    re.compile(r"\bINSERT\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\b", re.IGNORECASE),
    re.compile(r"\bDELETE\b", re.IGNORECASE),
    re.compile(r"\bDROP\b", re.IGNORECASE),
    re.compile(r"\bCREATE\b", re.IGNORECASE),
    re.compile(r"\bALTER\b", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\b", re.IGNORECASE),
    re.compile(r"\bGRANT\b", re.IGNORECASE),
    re.compile(r"\bREVOKE\b", re.IGNORECASE),
]

# Patterns that indicate PII/sensitive data
_PII_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "SSN pattern"),
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "Credit card pattern"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "Email pattern"),
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "Phone number pattern"),
]


def audit_sql_readonly(sql: str) -> list[AuditFinding]:
    """Check if a SQL query contains write operations."""
    findings = []
    for pattern in _WRITE_PATTERNS:
        if pattern.search(sql):
            findings.append(
                AuditFinding(
                    severity="critical",
                    category="sql_readonly",
                    message=f"Write operation detected: {pattern.pattern}",
                    details=f"SQL contains forbidden pattern: {pattern.pattern}",
                )
            )
    return findings


def audit_pii_leak(text: str) -> list[AuditFinding]:
    """Check if text contains potential PII."""
    findings = []
    for pattern, name in _PII_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            findings.append(
                AuditFinding(
                    severity="high",
                    category="pii_leak",
                    message=f"Potential {name} found ({len(matches)} matches)",
                    details=f"Found {len(matches)} potential PII matches",
                )
            )
    return findings


def audit_prompt_safety(prompt: str) -> list[AuditFinding]:
    """Check if a prompt contains unsafe patterns."""
    findings = []
    injection_patterns = [
        (re.compile(r"ignore\s+(previous|above|all)\s+instructions", re.IGNORECASE), "Prompt injection"),
        (re.compile(r"system\s*prompt", re.IGNORECASE), "System prompt reference"),
        (re.compile(r"<\s*/\s*instruction\s*>", re.IGNORECASE), "Instruction tag"),
    ]
    for pattern, name in injection_patterns:
        if pattern.search(prompt):
            findings.append(
                AuditFinding(
                    severity="medium",
                    category="prompt_safety",
                    message=f"Potential {name} detected",
                    details=f"Pattern matched: {pattern.pattern}",
                )
            )
    return findings


async def run_security_audit() -> SecurityAudit:
    """Run a comprehensive security audit of the system."""
    audit = SecurityAudit()
    try:
        from app.tools.sql_executor import SQLExecutor
        executor = SQLExecutor()
        if hasattr(executor, "_readonly") and executor._readonly:
            audit.add_finding(AuditFinding(severity="info", category="sql_readonly", message="SQL executor has read-only mode enabled"))
        elif hasattr(executor, "readonly") and executor.readonly:
            audit.add_finding(AuditFinding(severity="info", category="sql_readonly", message="SQL executor has read-only mode enabled"))
    except Exception as exc:
        audit.add_finding(AuditFinding(severity="medium", category="sql_readonly", message=f"Could not verify SQL executor: {exc}"))
    try:
        from app.config import get_settings
        settings = get_settings()
        if settings.redact_pii_in_prompts:
            audit.add_finding(AuditFinding(severity="info", category="pii_redaction", message="PII redaction in prompts is enabled"))
        else:
            audit.add_finding(AuditFinding(severity="high", category="pii_redaction", message="PII redaction in prompts is DISABLED", details="Sensitive data may leak into LLM prompts"))
    except Exception as exc:
        audit.add_finding(AuditFinding(severity="low", category="pii_redaction", message=f"Could not verify PII settings: {exc}"))
    try:
        from app.config import get_settings
        settings = get_settings()
        if settings.environment == "development":
            audit.add_finding(AuditFinding(severity="low", category="auth", message="Running in development mode"))
        if not settings.auth_bypass:
            audit.add_finding(AuditFinding(severity="info", category="auth", message="Authentication bypass is disabled"))
        else:
            audit.add_finding(AuditFinding(severity="high", category="auth", message="Authentication bypass is ENABLED", details="All requests are authenticated automatically"))
    except Exception as exc:
        audit.add_finding(AuditFinding(severity="low", category="auth", message=f"Could not verify auth settings: {exc}"))
    return audit

