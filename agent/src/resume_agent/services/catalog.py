from __future__ import annotations

from typing import Any


def editable_catalog(resume: dict[str, Any]) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for section in resume.get("sections", []):
        section_path = f"/sections/{section['id']}"
        if "body" in section:
            catalog.append({"path": f"{section_path}/body", "kind": "text"})
        if section.get("rows"):
            catalog.append({"path": f"{section_path}/rows", "kind": "collection"})
        for row in section.get("rows", []):
            catalog.append({"path": f"{section_path}/rows/{row['id']}/items", "kind": "text"})
        if section.get("entries"):
            catalog.append({"path": f"{section_path}/entries", "kind": "collection"})
        for entry in section.get("entries", []):
            entry_path = f"{section_path}/entries/{entry['id']}"
            catalog.append({"path": entry_path, "kind": "hideable"})
            if "summary" in entry:
                catalog.append({"path": f"{entry_path}/summary", "kind": "text"})
            for collection in ("items", "responsibilities"):
                values = entry.get(collection, [])
                if values:
                    catalog.append({"path": f"{entry_path}/{collection}", "kind": "collection"})
                for item in values:
                    catalog.append({"path": f"{entry_path}/{collection}/{item['id']}", "kind": "text_hideable"})
    return catalog

