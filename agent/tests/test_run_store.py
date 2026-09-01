import json

from resume_agent.services.run_store import create_run, safe_slug, write_target


def test_run_uses_jd_label_for_output_and_stays_inside_run_dir(tmp_path):
    run_dir = create_run("Google AI Agent", "Build reliable agents", b"master", root=tmp_path)
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert metadata["output_name"] == "google_ai_agent_resume.yaml"
    target = write_target(run_dir, metadata["output_name"], {"sections": []})
    assert target == run_dir / "google_ai_agent_resume.yaml"
    assert safe_slug("Google / AI Agent") == "google_ai_agent"
    assert safe_slug("字节跳动 AI Agent") == "字节跳动_ai_agent"
