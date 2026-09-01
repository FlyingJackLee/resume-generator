import copy

from resume_agent.paths import MASTER_RESUME_PATH
from resume_agent.services.master_resume import collect_facts, load_master_resume, prepare_working_resume


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

