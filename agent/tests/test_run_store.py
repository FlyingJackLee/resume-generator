import json

from resume_agent.services.run_store import (
    create_run,
    read_events,
    safe_slug,
    update_metadata,
    write_target,
)


def test_run_uses_jd_label_for_output_and_stays_inside_run_dir(tmp_path):
    run_dir = create_run("Google AI Agent", "Build reliable agents", b"master", root=tmp_path)
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert metadata["output_name"] == "google_ai_agent_resume.yaml"
    target = write_target(run_dir, metadata["output_name"], {"sections": []})
    assert target == run_dir / "google_ai_agent_resume.yaml"
    assert safe_slug("Google / AI Agent") == "google_ai_agent"
    assert safe_slug("字节跳动 AI Agent") == "字节跳动_ai_agent"


def test_create_run_stores_optional_company(tmp_path):
    run_dir = create_run(
        "Google AI Agent", "Build reliable agents", b"master", root=tmp_path, company="Google"
    )
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert metadata["company"] == "Google"
    assert metadata["notes"] == ""

    no_company = create_run("Meta ML", "Build reliable systems", b"master", root=tmp_path)
    metadata = json.loads((no_company / "run.json").read_text(encoding="utf-8"))
    assert metadata["company"] is None


def test_create_run_and_update_metadata_append_events(tmp_path):
    run_dir = create_run("Google AI Agent", "Build reliable agents", b"master", root=tmp_path)
    update_metadata(run_dir, status="ANALYZING", stage="JD Analyzer")
    update_metadata(run_dir, status="MATCHING", stage="Resume Matcher")

    events = read_events(run_dir)
    assert len(events) == 3
    assert events[0]["status"] == "INIT"
    assert events[1]["status"] == "ANALYZING"
    assert events[1]["stage"] == "JD Analyzer"
    assert events[2]["status"] == "MATCHING"
    assert all("timestamp" in event and "run_id" in event for event in events)


def test_read_events_returns_empty_list_when_no_log(tmp_path):
    run_dir = tmp_path / "run_empty"
    run_dir.mkdir()
    assert read_events(run_dir) == []
