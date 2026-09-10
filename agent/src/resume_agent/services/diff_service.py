from __future__ import annotations

from typing import Any

from resume_agent.models import ResumePatch

from .path_resolver import resolve_path
from .resume_labels import localized


def _member_label(member: Any) -> str:
    """A short human-readable label for one member of a reordered collection.

    Reorder targets a container (entries/rows), so the resolved value there is
    the whole list of member dicts, not text — pick out whichever field
    actually identifies the member to a person (title/label/org), falling
    back to its ID rather than the raw dict.
    """
    if not isinstance(member, dict):
        return str(member)
    for key in ("title", "label", "org"):
        text = localized(member.get(key))
        if text:
            return text
    return str(member.get("id", ""))


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
        if operation.op == "reorder":
            # The frontend renders original/revised by joining a list of
            # strings — a reorder's resolved value is the container's full
            # list of member dicts, so reduce each member to its label here
            # rather than let the raw dict get stringified downstream.
            if isinstance(original, list):
                original = [_member_label(member) for member in original]
            if isinstance(revised, list):
                revised = [_member_label(member) for member in revised]
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

