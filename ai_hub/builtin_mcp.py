from typing import Any, Dict, List, Tuple

from .builtins.registry import BuiltinSpec, get as get_spec, list_specs, to_choices


def get_builtin_definition(kind: str) -> Dict[str, Any]:
    spec = get_spec(kind)
    return {
        "kind": spec.kind,
        "label": spec.label,
        "name": spec.name,
        "version": spec.version,
        "description": spec.description,
        "tools": spec.tools,
        "resources": spec.resources,
        "call": spec.call,
    }


def list_builtin_definitions() -> List[Dict[str, Any]]:
    defs: List[Dict[str, Any]] = []
    for spec in list_specs():
        defs.append(
            {
                "kind": spec.kind,
                "label": spec.label,
                "name": spec.name,
                "version": spec.version,
                "description": spec.description,
            }
        )
    return defs


def builtin_choices(include_none: bool = True) -> List[Tuple[str, str]]:
    return to_choices(include_none=include_none)
