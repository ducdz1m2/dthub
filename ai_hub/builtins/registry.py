from __future__ import annotations

import importlib
import os
import pkgutil
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class BuiltinSpec:
    kind: str
    label: str
    name: str
    version: str
    description: str
    tools: Callable[[], List[Dict[str, Any]]]
    resources: Callable[[], List[Dict[str, Any]]]
    call: Callable[[str, Dict[str, Any]], Dict[str, Any]]


_REGISTRY: Dict[str, BuiltinSpec] = {}
_LOADED = False


def register(spec: BuiltinSpec) -> BuiltinSpec:
    kind = (spec.kind or "").strip().lower()
    if not kind:
        raise ValueError("builtin kind is required")
    _REGISTRY[kind] = spec
    return spec


def ensure_loaded() -> None:
    global _LOADED
    if _LOADED:
        return
    package_dir = os.path.dirname(__file__)
    for module in pkgutil.iter_modules([package_dir]):
        name = module.name
        if name.startswith("_") or name in {"registry", "template_builtin"}:
            continue
        importlib.import_module(f"{__package__}.{name}")
    _LOADED = True


def get(kind: str) -> BuiltinSpec:
    ensure_loaded()
    key = (kind or "").strip().lower()
    spec = _REGISTRY.get(key)
    if not spec:
        raise ValueError("unknown builtin kind")
    return spec


def list_specs() -> List[BuiltinSpec]:
    ensure_loaded()
    return sorted(_REGISTRY.values(), key=lambda s: (s.kind, s.label))


def to_choices(include_none: bool = True) -> List[tuple]:
    choices: List[tuple] = []
    if include_none:
        choices.append(("", "Không dùng node tích hợp"))
    for spec in list_specs():
        choices.append((spec.kind, spec.label))
    return choices
