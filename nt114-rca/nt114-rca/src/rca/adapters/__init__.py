"""Dataset adapters, registered by dataset id."""
from __future__ import annotations

from .base import Adapter

REGISTRY: dict[str, type[Adapter]] = {}


def register(cls: type[Adapter]) -> type[Adapter]:
    REGISTRY[cls.dataset_id] = cls
    return cls


def get(dataset_id: str) -> type[Adapter]:
    if dataset_id not in REGISTRY:
        _load_builtin()
    if dataset_id not in REGISTRY:
        raise KeyError(f"no adapter registered for dataset {dataset_id!r}")
    return REGISTRY[dataset_id]


def _load_builtin() -> None:
    from . import aiops2025, nezha, rca100, rcaeval  # noqa: F401
