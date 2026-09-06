"""API endpoints for specialist listing and invocation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user, get_db
from app.schemas.auth import AuthenticatedUser
from app.services.user_service import ensure_user

router = APIRouter(prefix="/specialists", tags=["specialists"])


class InvokeRequest(BaseModel):
    skill: str
    params: dict[str, Any] = {}


@router.get("/")
async def list_specialists(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """List all registered specialists with their capabilities."""
    await ensure_user(db, current_user)

    from app.specialists import specialist_registry

    specialists = specialist_registry.list(available_only=False)
    return {
        "specialists": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "capabilities": s.capabilities,
                "supported_data_types": s.supported_data_types,
                "tools": s.tools,
                "available": s.available,
            }
            for s in specialists
        ],
        "count": len(specialists),
    }


@router.get("/{specialist_id}")
async def get_specialist(
    specialist_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get details of a specific specialist."""
    await ensure_user(db, current_user)

    from app.specialists import specialist_registry

    spec = specialist_registry.metadata(specialist_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Specialist '{specialist_id}' not found")

    return {
        "id": spec.id,
        "name": spec.name,
        "description": spec.description,
        "capabilities": spec.capabilities,
        "supported_data_types": spec.supported_data_types,
        "tools": spec.tools,
        "available": spec.available,
    }


@router.post("/{specialist_id}/invoke")
async def invoke_specialist(
    specialist_id: str,
    body: InvokeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Invoke a specific skill on a specialist directly.

    Example request body::

        {
            "skill": "sentiment",
            "params": {"text": "This product is amazing!"}
        }

    Returns the raw skill output as JSON. All specialist skills are pure Python
    and execute in-process — no external API calls required.
    """
    await ensure_user(db, current_user)

    from app.specialists import specialist_registry, get_specialist_class

    spec = specialist_registry.metadata(specialist_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Specialist '{specialist_id}' not found")

    if not spec.available:
        raise HTTPException(
            status_code=503,
            detail=f"Specialist '{specialist_id}' is not currently available.",
        )

    cls = get_specialist_class(specialist_id)
    if cls is None:
        raise HTTPException(
            status_code=501,
            detail=f"Specialist '{specialist_id}' has no invokable implementation (pipeline-only).",
        )

    # Instantiate the specialist and look up the skill method
    instance = cls()

    # Skill methods are registered via the @skill decorator; find by name
    skill_method = None
    for attr_name in dir(instance):
        if attr_name.startswith("_"):
            continue
        attr = getattr(instance, attr_name, None)
        if callable(attr) and getattr(attr, "_skill_name", None) == body.skill:
            skill_method = attr
            break

    # Also try direct method name match as fallback
    if skill_method is None:
        skill_method = getattr(instance, body.skill, None)
        if not callable(skill_method):
            skill_method = None

    if skill_method is None:
        # List available skills
        available_skills = [
            getattr(getattr(instance, a, None), "_skill_name", a)
            for a in dir(instance)
            if not a.startswith("_") and callable(getattr(instance, a, None))
        ]
        raise HTTPException(
            status_code=404,
            detail=f"Skill '{body.skill}' not found on specialist '{specialist_id}'. "
            f"Available: {[s for s in available_skills if s]}",
        )

    try:
        result = await skill_method(**body.params)
    except TypeError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid parameters for skill '{body.skill}': {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Skill execution error: {exc}",
        ) from exc

    return {
        "specialist_id": specialist_id,
        "skill": body.skill,
        "result": result,
    }
