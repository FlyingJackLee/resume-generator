import copy

import pytest

from resume_agent.errors import PatchError
from resume_agent.models import PatchOperation, ResumePatch
from resume_agent.services import apply_patch, build_diff, load_master_resume, prepare_working_resume


def working_resume():
    return prepare_working_resume(load_master_resume())


def test_replace_is_evidence_backed_and_does_not_mutate_input():
    master = working_resume()
    original = copy.deepcopy(master)
    body = master["sections"][0]["body"]
    patch = ResumePatch(operations=[PatchOperation(
        op="replace",
        path="/sections/introduction/body",
        supported_by=body["supported_by"],
        reason="突出 Agent 经验",
        value={"zh": body["zh"], "en": body["en"]},
    )])
    candidate = apply_patch(master, patch)
    assert master == original
    assert candidate["sections"][0]["body"]["supported_by"] == body["supported_by"]
    assert build_diff(master, candidate, patch)[0]["reason"] == "突出 Agent 经验"


def test_protected_field_cannot_be_replaced():
    master = working_resume()
    fact_id = master["sections"][0]["body"]["supported_by"][0]
    patch = ResumePatch(operations=[PatchOperation(
        op="replace",
        path="/sections/work/entries/china_telecom_corporation_limited/title",
        supported_by=[fact_id],
        reason="伪造职位",
        value={"zh": "CTO", "en": "CTO"},
    )])
    with pytest.raises(PatchError, match="受保护字段"):
        apply_patch(master, patch)


def test_hide_removes_only_target_copy_item():
    master = working_resume()
    entries = next(section for section in master["sections"] if section["id"] == "work")["entries"]
    patch = ResumePatch(operations=[PatchOperation(
        op="hide",
        path="/sections/work/entries/china_telecom_corporation_limited",
        reason="与 JD 相关性较低",
    )])
    candidate = apply_patch(master, patch)
    candidate_entries = next(section for section in candidate["sections"] if section["id"] == "work")["entries"]
    assert len(candidate_entries) == len(entries) - 1
    assert len(entries) == 4


def test_reorder_requires_exact_existing_ids():
    master = working_resume()
    entries = next(section for section in master["sections"] if section["id"] == "projects")["entries"]
    ids = [entry["id"] for entry in entries]
    patch = ResumePatch(operations=[PatchOperation(
        op="reorder", path="/sections/projects/entries", reason="相关性排序", value=list(reversed(ids))
    )])
    candidate = apply_patch(master, patch)
    reordered = next(section for section in candidate["sections"] if section["id"] == "projects")["entries"]
    assert [entry["id"] for entry in reordered] == list(reversed(ids))


def test_restore_can_reinsert_an_item_hidden_from_candidate():
    master = working_resume()
    path = "/sections/work/entries/china_telecom_corporation_limited"
    hidden = apply_patch(master, ResumePatch(operations=[PatchOperation(
        op="hide", path=path, reason="temporary hide"
    )]))
    restored = apply_patch(
        hidden,
        ResumePatch(operations=[PatchOperation(op="restore", path=path, reason="restore")]),
        restore_source=master,
    )
    entries = next(section for section in restored["sections"] if section["id"] == "work")["entries"]
    assert entries[0]["id"] == "china_telecom_corporation_limited"
