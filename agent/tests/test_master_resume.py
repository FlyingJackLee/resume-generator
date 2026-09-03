import copy

from fakes import HappyProvider
from resume_agent.config import Settings
from resume_agent.paths import MASTER_RESUME_PATH
from resume_agent.services.master_resume import collect_facts, load_master_resume, prepare_working_resume
from resume_agent.services.master_resume import ensure_master_resume
from resume_agent.services.workflow_service import WorkflowService


def test_preparing_working_copy_never_changes_master_file_or_object():
    before_bytes = MASTER_RESUME_PATH.read_bytes()
    master = load_master_resume()
    original = copy.deepcopy(master)
    working = prepare_working_resume(master)
    assert master == original
    assert MASTER_RESUME_PATH.read_bytes() == before_bytes
    assert working != master
    assert working["sections"][0]["id"] == "introduction"
    assert len(collect_facts(working)) >= 20


def test_all_editable_text_has_stable_id_and_support():
    working = prepare_working_resume(load_master_resume())
    for section in working["sections"]:
        if "body" in section:
            assert section["body"]["id"] == "body"
            assert section["body"]["supported_by"]
        for row in section.get("rows", []):
            assert row["id"]
            assert row["items"]["supported_by"]
        for entry in section.get("entries", []):
            assert entry["id"]
            for collection in ("items", "responsibilities"):
                for item in entry.get(collection, []):
                    assert item["id"]
                    assert item["supported_by"]


def test_missing_master_is_created_from_sample(tmp_path):
    sample = tmp_path / "resume.sample.yaml"
    sample.write_text("meta: {}\nsections: []\n", encoding="utf-8")
    master = tmp_path / "resume.yaml"
    assert ensure_master_resume(master, sample) == master
    assert master.read_text(encoding="utf-8") == sample.read_text(encoding="utf-8")


def test_editor_draft_publishes_only_after_confirmation_and_can_roll_back(tmp_path):
    master = tmp_path / "resume.yaml"
    master.write_bytes(MASTER_RESUME_PATH.read_bytes())
    service = WorkflowService(
        HappyProvider(), Settings(api_key="fake"), runs_root=tmp_path / "runs", master_path=master
    )
    run_id = service.get_or_create_editor_draft()["run_id"]
    original = master.read_text(encoding="utf-8")
    changed = service.get_editor_draft(run_id)
    changed["meta"]["name"]["zh"] = "测试姓名"
    service.update_editor_draft(run_id, changed)
    assert master.read_text(encoding="utf-8") == original

    service.publish_editor_draft(run_id, "测试发布")
    assert load_master_resume(master)["meta"]["name"]["zh"] == "测试姓名"
    versions = service.editor_versions(run_id)
    assert len(versions) == 2

    service.rollback_editor_version(run_id, versions[0]["id"])
    assert load_master_resume(master)["meta"]["name"]["zh"] != "测试姓名"
