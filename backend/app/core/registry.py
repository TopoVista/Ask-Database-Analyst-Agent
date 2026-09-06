"""Tool and specialist registries.

A *Tool* is a callable capability with declared input/output semantics.
A *Skill* is a reusable analysis workflow composed of tools.
A *Specialist* is configuration (not a model): prompts + skills + validators
describing one expert role the orchestration layer can route to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolSpec:
    id: str
    name: str
    description: str
    input_schema: dict[str, str] = field(default_factory=dict)
    output_schema: dict[str, str] = field(default_factory=dict)
    permissions: frozenset[str] = frozenset({"read"})
    # Async callable: **kwargs -> Any
    executor: Callable[..., Any] | None = None

    async def execute(self, **kwargs: Any) -> Any:
        if self.executor is None:
            raise NotImplementedError(f"tool '{self.id}' has no executor bound")
        return await self.executor(**kwargs)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec, *, overwrite: bool = False) -> None:
        if spec.id in self._tools and not overwrite:
            raise ValueError(f"tool '{spec.id}' already registered")
        self._tools[spec.id] = spec

    def get(self, tool_id: str) -> ToolSpec | None:
        return self._tools.get(tool_id)

    def require(self, tool_id: str) -> ToolSpec:
        tool = self._tools.get(tool_id)
        if tool is None:
            raise KeyError(f"tool '{tool_id}' is not registered")
        return tool

    def list(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def filter(self, tool_ids: list[str]) -> list[ToolSpec]:
        return [self._tools[t] for t in tool_ids if t in self._tools]


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillSpec:
    id: str
    name: str
    description: str
    tools: list[str] = field(default_factory=list)
    # Async callable operating on a workflow context.
    runner: Callable[..., Any] | None = None

    async def run(self, **kwargs: Any) -> Any:
        if self.runner is None:
            raise NotImplementedError(f"skill '{self.id}' has no runner bound")
        return await self.runner(**kwargs)


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, SkillSpec] = {}

    def register(self, spec: SkillSpec, *, overwrite: bool = False) -> None:
        if spec.id in self._skills and not overwrite:
            raise ValueError(f"skill '{spec.id}' already registered")
        self._skills[spec.id] = spec

    def get(self, skill_id: str) -> SkillSpec | None:
        return self._skills.get(skill_id)

    def require(self, skill_id: str) -> SkillSpec:
        skill = self._skills.get(skill_id)
        if skill is None:
            raise KeyError(f"skill '{skill_id}' is not registered")
        return skill

    def list(self) -> list[SkillSpec]:
        return list(self._skills.values())


def skill(name: str, *, description: str = "", tools: list[str] | None = None):
    """Decorator that marks a method as a skill.

    Usage::

        @skill("tokenize")
        async def tokenize(self, text: str) -> dict:
            ...

    The decorated method gains a ``__skill__`` attribute with the skill metadata.
    """
    import functools

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper.__skill__ = SkillSpec(
            id=name,
            name=name,
            description=description or func.__doc__ or "",
            tools=tools or [],
            runner=wrapper,
        )
        wrapper.__skill_name__ = name
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Specialists
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Specialist:
    id: str
    name: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    supported_data_types: list[str] = field(default_factory=lambda: ["tabular"])
    tools: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    system_prompt: str = ""
    validators: list[str] = field(default_factory=list)
    # False until a real workflow backs every declared capability. The router
    # never selects an unavailable specialist; the API reports it as planned.
    available: bool = True


class SpecialistRegistry:
    """Registry of specialist configurations.

    Supports two registration styles:

    Imperative::

        registry.register(Specialist(id="x", ...))

    Decorator (binds metadata to a class)::


        @registry.register(id="x", name="X", description="", capabilities=[...])
        class X:
            ...

    ``get(id)`` returns the bound class when registered via decorator,
    otherwise the ``Specialist`` spec. ``metadata(id)`` always returns the
    ``Specialist`` configuration (or ``None``).
    """

    def __init__(self) -> None:
        self._specialists: dict[str, Specialist] = {}
        self._classes: dict[str, type] = {}

    def register(
        self,
        specialist: Specialist | None = None,
        *,
        overwrite: bool = False,
        **kwargs: Any,
    ) -> Any:
        if specialist is None:
            # Decorator factory form.
            def decorator(cls: type) -> type:
                spec = Specialist(
                    id=kwargs.get("id", cls.__name__),
                    name=kwargs.get("name", cls.__name__),
                    description=kwargs.get("description", ""),
                    capabilities=list(kwargs.get("capabilities", [])),
                    supported_data_types=list(kwargs.get("supported_data_types", ["tabular"])),
                    tools=list(kwargs.get("tools", [])),
                    skills=list(kwargs.get("skills", [])),
                    system_prompt=kwargs.get("system_prompt", ""),
                    validators=list(kwargs.get("validators", [])),
                )
                if spec.id in self._specialists and not overwrite:
                    raise ValueError(f"specialist '{spec.id}' already registered")
                self._specialists[spec.id] = spec
                self._classes[spec.id] = cls
                cls.__specialist__ = spec  # type: ignore[attr-defined]
                return cls

            return decorator

        if specialist.id in self._specialists and not overwrite:
            raise ValueError(f"specialist '{specialist.id}' already registered")
        self._specialists[specialist.id] = specialist
        return specialist

    def get(self, specialist_id: str) -> Any:
        return self._classes.get(specialist_id) or self._specialists.get(specialist_id)

    def metadata(self, specialist_id: str) -> Specialist | None:
        return self._specialists.get(specialist_id)

    def ids(self) -> list[str]:
        return list(self._specialists.keys())

    def list(self, *, available_only: bool = False) -> list[Specialist]:
        items = self._specialists.values()
        if available_only:
            items = [s for s in items if s.available]
        return list(items)

    def find_by_capability(self, capability: str) -> list[Specialist]:
        return [s for s in self._specialists.values() if capability in s.capabilities and s.available]
