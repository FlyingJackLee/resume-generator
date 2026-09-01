from resume_agent.models import PatchOperation, ResumePatch
from resume_agent.services import apply_patch, load_master_resume, prepare_working_resume, validate_candidate


def test_unchanged_prepared_master_passes():
    master = prepare_working_resume(load_master_resume())
    result = validate_candidate(master, master)
    assert result.passed, result.model_dump()


def test_new_number_and_technology_without_support_fail():
    master = prepare_working_resume(load_master_resume())
    body = master["sections"][0]["body"]
    patch = ResumePatch(operations=[PatchOperation(
        op="replace",
        path="/sections/introduction/body",
        supported_by=body["supported_by"],
        reason="不安全的测试修改",
        value={"zh": body["zh"] + " 使用 Rust 提升性能 99%。", "en": body["en"] + " Used Rust for a 99% gain."},
    )])
    candidate = apply_patch(master, patch)
    result = validate_candidate(master, candidate)
    assert not result.passed
    assert {issue.code for issue in result.issues} >= {"V03", "V04"}


def test_manual_edit_of_protected_field_fails():
    master = prepare_working_resume(load_master_resume())
    candidate = prepare_working_resume(load_master_resume())
    work = next(section for section in candidate["sections"] if section["id"] == "work")
    work["entries"][0]["title"]["en"] = "Chief Technology Officer"
    result = validate_candidate(master, candidate)
    assert not result.passed
    assert any(issue.code == "V02" for issue in result.issues)


def test_bilingual_fact_can_support_english_technology_wording():
    master = prepare_working_resume(load_master_resume())
    projects = next(section for section in master["sections"] if section["id"] == "projects")
    entry = next(item for item in projects["entries"] if item["id"] == "ai_agent_full_stack_development")
    summary = entry["summary"]
    support = [summary["supported_by"][0], entry["responsibilities"][1]["supported_by"][0]]
    patch = ResumePatch(operations=[PatchOperation(
        op="replace",
        path="/sections/projects/entries/ai_agent_full_stack_development/summary",
        supported_by=support,
        reason="突出工具调用与安全网关",
        value={
            "zh": summary["zh"] + "，包括统一工具调用与安全网关。",
            "en": summary["en"] + " Includes unified tool calling and security gateway.",
        },
    )])
    candidate = apply_patch(master, patch)
    result = validate_candidate(master, candidate)
    assert not any(issue.code == "V03" for issue in result.issues), result.model_dump()
