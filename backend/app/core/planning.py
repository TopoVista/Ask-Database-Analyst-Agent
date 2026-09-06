"""Planning and validation value objects for the orchestration layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PlanStep:
    id: str
    description: str
    specialist: str | None = None
    skill: str | None = None
    tools: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskPlan:
    question: str
    steps: list[PlanStep] = field(default_factory=list)
    specialists: list[str] = field(default_factory=list)
    max_iterations: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "steps": [s.to_dict() for s in self.steps],
            "specialists": self.specialists,
            "max_iterations": self.max_iterations,
        }


@dataclass
class ExecutionResult:
    step_id: str
    success: bool
    output: Any = None
    error: str | None = None
    tool_calls: list[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationIssue:
    severity: str  # "error" | "warning" | "info"
    check: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def add(self, severity: str, check: str, message: str) -> None:
        self.issues.append(ValidationIssue(severity=severity, check=check, message=message))
        if severity == "error":
            self.passed = False

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "issues": [i.to_dict() for i in self.issues]}
