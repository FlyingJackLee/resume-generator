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

