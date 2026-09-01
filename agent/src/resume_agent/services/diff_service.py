from __future__ import annotations

from typing import Any

from resume_agent.models import ResumePatch

from .path_resolver import resolve_path


def build_diff(
    master: dict[str, Any], candidate: dict[str, Any], patch: ResumePatch
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for operation in patch.operations:
        original: Any = None
        revised: Any = None
        try:
            parent, leaf = resolve_path(master, operation.path)
            original = parent[leaf]
        except Exception:
            pass
        try:
            parent, leaf = resolve_path(candidate, operation.path)
            revised = parent[leaf]
        except Exception:
            pass
        result.append(
            {
                "op": operation.op,
                "path": operation.path,
                "original": original,
                "revised": revised,
                "reason": operation.reason,
                "supported_by": operation.supported_by,
            }
        )
    return result

