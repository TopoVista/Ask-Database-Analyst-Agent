"""Core abstractions shared by the orchestration layer.

These are deliberately lightweight dataclasses + registries. They wrap the
existing tools/agents rather than replacing them, so existing functionality
keeps working unchanged.
"""

from app.core.artifacts import Artifact, ArtifactStore
from app.core.planning import ExecutionResult, PlanStep, TaskPlan, ValidationResult
from app.core.registry import (
    SkillRegistry,
    SkillSpec,
    Specialist,
    SpecialistRegistry,
    ToolRegistry,
    ToolSpec,
)

__all__ = [
    "Artifact",
    "ArtifactStore",
    "ExecutionResult",
    "PlanStep",
    "TaskPlan",
    "ValidationResult",
    "SkillRegistry",
    "SkillSpec",
    "Specialist",
    "SpecialistRegistry",
    "ToolRegistry",
    "ToolSpec",
]
