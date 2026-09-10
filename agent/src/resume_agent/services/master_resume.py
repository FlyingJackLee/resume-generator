from __future__ import annotations

import copy
import re
import shutil
from pathlib import Path
from typing import Any

import yaml

from resume_agent.errors import ResumeAgentError
from resume_agent.paths import MASTER_RESUME_PATH, MASTER_RESUME_SAMPLE_PATH


def ensure_master_resume(
    path: Path = MASTER_RESUME_PATH, sample_path: Path = MASTER_RESUME_SAMPLE_PATH
) -> Path:
    """Create the local private resume from the committed sample on first run."""
    if path.exists():
        return path
    if not sample_path.exists():
        raise ResumeAgentError(f"未找到简历示例文件：{sample_path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(sample_path, path)
    return path


def load_master_resume(path: Path = MASTER_RESUME_PATH) -> dict[str, Any]:
    """Load the canonical resume read-only. This module never writes to *path*."""
    ensure_master_resume(path)
    with path.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict) or not isinstance(data.get("sections"), list):
        raise ResumeAgentError(f"Master Resume 格式无效：{path}")
    return data


def _slug(value: str, fallback: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return value[:48] or fallback


def _english(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("en") or value.get("zh") or "")
    return str(value or "")


def _fact(fact_id: str, kind: str, statement: dict[str, str]) -> dict[str, Any]:
    return {"id": fact_id, "type": kind, "statement": copy.deepcopy(statement)}


def _annotate_text(
    value: dict[str, Any], item_id: str, fact_id: str
) -> dict[str, Any]:
    value["id"] = item_id
    value["supported_by"] = [fact_id]
    return value


def prepare_working_resume(master: dict[str, Any]) -> dict[str, Any]:
    """Create an ID- and fact-enriched copy without mutating the Master Resume."""
    result = copy.deepcopy(master)
    used_section_ids: set[str] = set()
    for section_index, section in enumerate(result["sections"], start=1):
        title = _english(section.get("title"))
        section_id = _slug(title, f"section_{section_index}")
        if section_id in used_section_ids:
            section_id = f"{section_id}_{section_index}"
        used_section_ids.add(section_id)
        section["id"] = section_id
        section["facts"] = []

        if section.get("type") == "paragraph" and isinstance(section.get("body"), dict):
            fact_id = f"fact_{section_id}_body"
            section["facts"].append(_fact(fact_id, "summary", section["body"]))
            _annotate_text(section["body"], "body", fact_id)

        for row_index, row in enumerate(section.get("rows", []), start=1):
            row_id = _slug(_english(row.get("label")), f"row_{row_index}")
            row["id"] = row_id
            if isinstance(row.get("items"), dict):
                fact_id = f"fact_{section_id}_{row_id}"
                section["facts"].append(_fact(fact_id, "technology", row["items"]))
                _annotate_text(row["items"], "items", fact_id)

        used_entry_ids: set[str] = set()
        for entry_index, entry in enumerate(section.get("entries", []), start=1):
            identity = _english(entry.get("org")) or _english(entry.get("title"))
            entry_id = _slug(identity, f"entry_{entry_index}")
            if entry_id in used_entry_ids:
                entry_id = f"{entry_id}_{entry_index}"
            used_entry_ids.add(entry_id)
            entry["id"] = entry_id
            entry["facts"] = []
            if isinstance(entry.get("summary"), dict):
                fact_id = f"fact_{section_id}_{entry_id}_summary"
                entry["facts"].append(_fact(fact_id, "summary", entry["summary"]))
                _annotate_text(entry["summary"], "summary", fact_id)
            for collection in ("items", "responsibilities"):
                for item_index, item in enumerate(entry.get(collection, []), start=1):
                    item_id = f"{collection}_{item_index:02d}"
                    fact_id = f"fact_{section_id}_{entry_id}_{item_id}"
                    entry["facts"].append(_fact(fact_id, "responsibility", item))
                    _annotate_text(item, item_id, fact_id)
    return result


def collect_facts(resume: dict[str, Any]) -> dict[str, dict[str, Any]]:
    facts: dict[str, dict[str, Any]] = {}
    for section in resume.get("sections", []):
        for fact in section.get("facts", []):
            facts[fact["id"]] = fact
        for entry in section.get("entries", []):
            for fact in entry.get("facts", []):
                facts[fact["id"]] = fact
    return facts
