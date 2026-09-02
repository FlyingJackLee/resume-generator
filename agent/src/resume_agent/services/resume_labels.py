from __future__ import annotations

from typing import Any


def localized(value: Any) -> str:
    if isinstance(value, dict):
        return value.get("zh") or value.get("en") or ""
    return str(value or "")


def path_label(resume: dict[str, Any], path: str) -> str:
    parts = path.strip("/").split("/")
    if len(parts) < 2:
        return path
    section = next((item for item in resume["sections"] if item.get("id") == parts[1]), None)
    if not section:
        return path
    labels = [localized(section.get("title"))]
    if "rows" in parts:
        index = parts.index("rows")
        if len(parts) > index + 1:
            row = next((item for item in section.get("rows", []) if item.get("id") == parts[index + 1]), None)
            if row:
                labels.append(localized(row.get("label")))
    if "entries" in parts:
        index = parts.index("entries")
        if len(parts) > index + 1:
            entry = next((item for item in section.get("entries", []) if item.get("id") == parts[index + 1]), None)
            if entry:
                labels.append(localized(entry.get("title") or entry.get("org")))
                for collection in ("items", "responsibilities"):
                    if collection in parts and parts[-1] != collection:
                        item = next((value for value in entry.get(collection, []) if value.get("id") == parts[-1]), None)
                        if item:
                            labels.append(localized(item)[:42] + "…")
            if parts[-1] == "summary":
                labels.append("项目简介")
    if parts[-1] == "body":
        labels.append("正文")
    return " › ".join(filter(None, labels))
