from __future__ import annotations

import copy
from typing import Any

from resume_agent.errors import PatchError
from resume_agent.models import BilingualText, ResumePatch

from .master_resume import collect_facts
from .path_resolver import resolve_collection, resolve_path


EDITABLE_SUFFIXES = ("/body", "/items", "/summary")
EDITABLE_COLLECTION_MARKERS = ("/items/", "/responsibilities/")
HIDEABLE_MARKERS = ("/entries/", "/items/", "/responsibilities/")


def _replace_allowed(path: str) -> bool:
    return path.endswith(EDITABLE_SUFFIXES) or any(
        marker in path for marker in EDITABLE_COLLECTION_MARKERS
    )


def _hide_allowed(path: str) -> bool:
    return any(marker in path for marker in HIDEABLE_MARKERS)


def _assert_support(fact_ids: list[str], facts: dict[str, Any], path: str) -> None:
    unknown = sorted(set(fact_ids) - facts.keys())
    if unknown:
        raise PatchError(f"{path} 引用了不存在的 facts：{', '.join(unknown)}")


def apply_patch(
    master_working_copy: dict[str, Any],
    patch: ResumePatch,
    *,
    restore_source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministically apply a patch to a copy; never mutate its input."""
    result = copy.deepcopy(master_working_copy)
    source = restore_source or master_working_copy
    facts = collect_facts(source)
    touched: set[str] = set()
    for operation in patch.operations:
        if operation.path in touched and operation.op != "restore":
            raise PatchError(f"同一路径被重复修改：{operation.path}")
        touched.add(operation.path)
        _assert_support(operation.supported_by, facts, operation.path)

        if operation.op == "replace":
            if not _replace_allowed(operation.path):
                raise PatchError(f"试图修改受保护字段：{operation.path}")
            parent, leaf = resolve_path(result, operation.path)
            current = parent[leaf]
            if not isinstance(current, dict) or "zh" not in current or "en" not in current:
                raise PatchError(f"replace 目标不是双语文本：{operation.path}")
            assert isinstance(operation.value, BilingualText)
            updated = operation.value.model_dump()
            updated["id"] = current.get("id", str(leaf))
            updated["supported_by"] = operation.supported_by
            parent[leaf] = updated

        elif operation.op == "reorder":
            collection = resolve_collection(result, operation.path)
            assert isinstance(operation.value, list)
            current_ids = [item.get("id") for item in collection]
            if len(operation.value) != len(set(operation.value)):
                raise PatchError(f"reorder 包含重复 ID：{operation.path}")
            if set(operation.value) != set(current_ids):
                raise PatchError(f"reorder 必须完整且只能包含现有 ID：{operation.path}")
            by_id = {item["id"]: item for item in collection}
            collection[:] = [by_id[item_id] for item_id in operation.value]

        elif operation.op == "hide":
            if not _hide_allowed(operation.path):
                raise PatchError(f"不允许隐藏该字段：{operation.path}")
            parent, leaf = resolve_path(result, operation.path)
            if not isinstance(parent, list) or not isinstance(leaf, int):
                raise PatchError(f"hide path 必须指向条目：{operation.path}")
            parent.pop(leaf)

        elif operation.op == "restore":
            # Every candidate is rebuilt from Master + approved operations. A restore
            # therefore means "do not apply an earlier operation to this path".
            source_parent, source_leaf = resolve_path(source, operation.path)
            try:
                target_parent, target_leaf = resolve_path(result, operation.path)
                target_parent[target_leaf] = copy.deepcopy(source_parent[source_leaf])
            except PatchError:
                parts = operation.path.strip("/").split("/")
                collection_path = "/" + "/".join(parts[:-1])
                source_collection = resolve_collection(source, collection_path)
                target_collection = resolve_collection(result, collection_path)
                source_index = next(
                    index for index, item in enumerate(source_collection) if item.get("id") == parts[-1]
                )
                target_collection.insert(
                    min(source_index, len(target_collection)), copy.deepcopy(source_collection[source_index])
                )
    return result
