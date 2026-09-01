from __future__ import annotations

from typing import Any

from resume_agent.errors import PatchError


COLLECTIONS = {"sections", "rows", "entries", "items", "responsibilities"}


def find_by_id(items: list[dict[str, Any]], object_id: str, path: str) -> int:
    matches = [index for index, item in enumerate(items) if item.get("id") == object_id]
    if len(matches) != 1:
        raise PatchError(f"路径对象不存在或 ID 不唯一：{path}")
    return matches[0]


def resolve_path(root: dict[str, Any], path: str) -> tuple[Any, str | int]:
    """Resolve an ID-based slash path and return its parent and leaf key/index."""
    parts = [part for part in path.strip("/").split("/") if part]
    if not parts or parts[0] != "sections":
        raise PatchError(f"Patch path 必须从 sections 开始：{path}")
    node: Any = root
    index = 0
    while index < len(parts):
        part = parts[index]
        if not isinstance(node, dict) or part not in node:
            raise PatchError(f"Patch path 不存在：{path}")
        if index == len(parts) - 1:
            return node, part
        child = node[part]
        if isinstance(child, list):
            object_id = parts[index + 1]
            item_index = find_by_id(child, object_id, path)
            if index + 1 == len(parts) - 1:
                return child, item_index
            node = child[item_index]
            index += 2
        else:
            node = child
            index += 1
    raise PatchError(f"Patch path 不存在：{path}")


def resolve_collection(root: dict[str, Any], path: str) -> list[dict[str, Any]]:
    parent, leaf = resolve_path(root, path)
    value = parent[leaf]
    if leaf not in COLLECTIONS or not isinstance(value, list):
        raise PatchError(f"reorder path 必须指向集合：{path}")
    return value
