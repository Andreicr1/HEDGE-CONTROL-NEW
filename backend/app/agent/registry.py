from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.agent.schemas import (
    CapabilityDefinition,
    CapabilityExecutionRequest,
    CapabilityExecutionResult,
)

CapabilityContextBuilder = Callable[[Session, UUID | None, dict], dict]
CapabilityHandler = Callable[
    [Session, CapabilityExecutionRequest, dict, dict, UUID],
    CapabilityExecutionResult,
]


@dataclass(frozen=True)
class CapabilityRegistration:
    metadata: CapabilityDefinition
    handler: CapabilityHandler
    context_builder: CapabilityContextBuilder | None = None


_CAPABILITY_REGISTRY: dict[str, CapabilityRegistration] = {}


def register_capability(registration: CapabilityRegistration) -> None:
    _CAPABILITY_REGISTRY[registration.metadata.name] = registration


def get_capability(name: str) -> CapabilityRegistration:
    return _CAPABILITY_REGISTRY[name]


def has_capability(name: str) -> bool:
    return name in _CAPABILITY_REGISTRY


def iter_capabilities() -> list[CapabilityRegistration]:
    return sorted(_CAPABILITY_REGISTRY.values(), key=lambda item: item.metadata.name)
