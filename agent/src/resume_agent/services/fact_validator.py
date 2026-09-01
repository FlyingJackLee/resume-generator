from __future__ import annotations

import re
from typing import Any

from resume_agent.models import ValidationIssue, ValidationResult

from .master_resume import collect_facts


PROTECTED_SECTION_KEYS = ("type", "title", "org_first", "page_break_before")
PROTECTED_ENTRY_KEYS = ("title", "org", "location", "date", "link", "degree")
WORD_PATTERN = re.compile(r"(?<![\w])(?:[A-Za-z][A-Za-z0-9.+#/-]{1,})(?![\w])")
NUMBER_PATTERN = re.compile(r"(?<!\w)\d+(?:[.,]\d+)?%?(?!\w)")
STRONG_ROLE_TERMS = {
    "主导", "独立完成", "负责人", "owned", "led", "architected", "spearheaded"
}
COMMON_TECH_TERMS = {
    "rust", "golang", "scala", "kotlin", "pytorch", "tensorflow", "pandas",
    "mongodb", "dynamodb", "snowflake", "terraform", "ansible", "grpc",
    "graphql", "aws", "azure", "gcp", "spark", "hadoop", "airflow",
}
TECH_TRANSLATION_HINTS = {
    "agent": ("智能体",),
    "calling": ("调用",),
    "cloud": ("云",),
    "embedding": ("嵌入", "向量"),
    "gateway": ("网关",),
    "retrieval": ("检索",),
    "security": ("安全",),
    "token": ("token", "令牌"),
    "workflow": ("工作流",),
}


def _issue(code: str, severity: str, path: str, message: str) -> ValidationIssue:
    return ValidationIssue(code=code, severity=severity, path=path, message=message)  # type: ignore[arg-type]


def _by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item.get("id", ""): item for item in items}


def _text(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    return " ".join(str(value.get(lang, "")) for lang in ("zh", "en"))


def _validate_text(
    value: dict[str, Any],
    path: str,
    facts: dict[str, dict[str, Any]],
    technology_terms: set[str],
    issues: list[ValidationIssue],
) -> None:
    support = value.get("supported_by")
    if not isinstance(support, list) or not support:
        issues.append(_issue("V01", "critical", path, "文本缺少 supported_by"))
        return
    unknown = [fact_id for fact_id in support if fact_id not in facts]
    if unknown:
        issues.append(_issue("V01", "critical", path, f"supported_by 不存在：{unknown}"))
        return
    evidence = " ".join(_text(facts[fact_id].get("statement")) for fact_id in support)
    current = _text(value)
    evidence_tech = {token.casefold() for token in WORD_PATTERN.findall(evidence)}
    new_tech = sorted(
        token
        for token in WORD_PATTERN.findall(current)
        if token.casefold() in technology_terms
        and token.casefold() not in evidence_tech
        and not any(
            hint.casefold() in evidence.casefold()
            for hint in TECH_TRANSLATION_HINTS.get(token.casefold(), ())
        )
    )
    if new_tech:
        issues.append(_issue("V03", "high", path, f"技术词缺少所选事实支持：{new_tech}"))
    evidence_numbers = set(NUMBER_PATTERN.findall(evidence))
    new_numbers = sorted(set(NUMBER_PATTERN.findall(current)) - evidence_numbers)
    if new_numbers:
        issues.append(_issue("V04", "critical", path, f"数字缺少所选事实支持：{new_numbers}"))
    evidence_folded = evidence.casefold()
    unsupported_strength = sorted(
        term for term in STRONG_ROLE_TERMS if term in current.casefold() and term not in evidence_folded
    )
    if unsupported_strength:
        issues.append(_issue("V06", "high", path, f"角色强度升级缺少支持：{unsupported_strength}"))


def validate_candidate(master: dict[str, Any], candidate: dict[str, Any]) -> ValidationResult:
    """Validate a working candidate against its immutable prepared Master copy."""
    issues: list[ValidationIssue] = []
    facts = collect_facts(master)
    technology_terms = set(COMMON_TECH_TERMS)
    for fact in facts.values():
        if fact.get("type") == "technology":
            technology_terms.update(
                token.casefold() for token in WORD_PATTERN.findall(_text(fact.get("statement")))
            )
    master_sections = _by_id(master.get("sections", []))
    candidate_sections = _by_id(candidate.get("sections", []))
    if set(candidate_sections) != set(master_sections):
        issues.append(_issue("V02", "critical", "/sections", "不得新增或删除顶级 section"))
    for section_id, section in candidate_sections.items():
        original = master_sections.get(section_id)
        if not original:
            continue
        for key in PROTECTED_SECTION_KEYS:
            if section.get(key) != original.get(key):
                issues.append(_issue("V02", "critical", f"/sections/{section_id}/{key}", "受保护字段被修改"))
        if isinstance(section.get("body"), dict):
            _validate_text(section["body"], f"/sections/{section_id}/body", facts, technology_terms, issues)
        original_rows = _by_id(original.get("rows", []))
        for row in section.get("rows", []):
            row_id = row.get("id", "")
            if row_id not in original_rows or row.get("label") != original_rows[row_id].get("label"):
                issues.append(_issue("V02", "critical", f"/sections/{section_id}/rows/{row_id}", "技能分类被新增或修改"))
            if isinstance(row.get("items"), dict):
                _validate_text(row["items"], f"/sections/{section_id}/rows/{row_id}/items", facts, technology_terms, issues)
        original_entries = _by_id(original.get("entries", []))
        for entry in section.get("entries", []):
            entry_id = entry.get("id", "")
            original_entry = original_entries.get(entry_id)
            if not original_entry:
                issues.append(_issue("V02", "critical", f"/sections/{section_id}/entries/{entry_id}", "新增了 Master 中不存在的条目"))
                continue
            for key in PROTECTED_ENTRY_KEYS:
                if entry.get(key) != original_entry.get(key):
                    issues.append(_issue("V02", "critical", f"/sections/{section_id}/entries/{entry_id}/{key}", "受保护字段被修改"))
            if isinstance(entry.get("summary"), dict):
                _validate_text(entry["summary"], f"/sections/{section_id}/entries/{entry_id}/summary", facts, technology_terms, issues)
            for collection in ("items", "responsibilities"):
                for item in entry.get(collection, []):
                    _validate_text(item, f"/sections/{section_id}/entries/{entry_id}/{collection}/{item.get('id', '')}", facts, technology_terms, issues)
    passed = not any(issue.severity in {"critical", "high"} for issue in issues)
    return ValidationResult(passed=passed, issues=issues)
