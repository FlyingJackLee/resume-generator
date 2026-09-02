import json

from resume_agent.config import Settings
from resume_agent.models import ResumePatch, RewriteStrategy
from resume_agent.services.workflow_service import WorkflowService

from fakes import HappyProvider


def make_service(tmp_path):
    settings = Settings(api_key="fake", hiring_threshold=85, max_iterations=2)
    return WorkflowService(HappyProvider(), settings, runs_root=tmp_path)


def test_two_human_gates_and_named_final_output(tmp_path):
    service = make_service(tmp_path)
    created = service.create("Google AI Agent", "We need a senior engineer to build reliable AI agents.")
    run_id = created["run_id"]
    assert created["status"] == "ANALYZING"

    service.analyze(run_id)
    assert service.get(run_id)["status"] == "WAITING_STRATEGY_APPROVAL"
    assert not (service.resolve_run(run_id) / "candidate_resume.yaml").exists()

    service.approve_strategy(run_id)
    service.compile(run_id)
    reviewed = service.get(run_id)
    assert reviewed["status"] == "WAITING_FINAL_APPROVAL"
    assert reviewed["hiring_score"] == 92
    assert not (service.resolve_run(run_id) / "google_ai_agent_resume.yaml").exists()

    completed = service.approve_final(run_id)
    assert completed["status"] == "COMPLETED"
    assert completed["target_file"] == "google_ai_agent_resume.yaml"
    assert (service.resolve_run(run_id) / completed["target_file"]).exists()


def test_final_cannot_be_approved_before_gate(tmp_path):
    service = make_service(tmp_path)
    run_id = service.create("Google AI Agent", "A sufficiently long pasted job description.")["run_id"]
    try:
        service.approve_final(run_id)
    except Exception as exc:
        assert "不能批准最终版本" in str(exc)
    else:
        raise AssertionError("approve_final should have failed")


def test_human_strategy_allows_semantically_normalized_safe_keyword(tmp_path):
    service = make_service(tmp_path)
    run_id = service.create("Google AI Agent", "A sufficiently long pasted job description.")["run_id"]
    service.analyze(run_id)
    strategy = RewriteStrategy.model_validate_json(
        (service.resolve_run(run_id) / "rewrite_strategy.json").read_text(encoding="utf-8")
    )
    strategy.safe_keywords.append("分布式系统")
    assert service.revise_strategy(run_id, strategy)["status"] == "WAITING_STRATEGY_APPROVAL"


class AlwaysInvalidProvider(HappyProvider):
    def complete(self, *, system, user, output_type, temperature):
        if output_type is ResumePatch:
            self.calls.append(output_type.__name__)
            return ResumePatch.model_validate({
                "operations": [{
                    "op": "replace",
                    "path": "/sections/introduction/body",
                    "supported_by": ["fact_introduction_body"],
                    "reason": "unsafe",
                    "value": {
                        "zh": self.body["zh"] + " 使用 Rust 获得 99% 提升。",
                        "en": self.body["en"] + " Used Rust for a 99% gain.",
                    },
                }]
            })
        return super().complete(system=system, user=user, output_type=output_type, temperature=temperature)


def test_validator_rework_is_bounded_to_two_editor_attempts(tmp_path):
    provider = AlwaysInvalidProvider()
    settings = Settings(api_key="fake", max_iterations=2)
    service = WorkflowService(provider, settings, runs_root=tmp_path)
    run_id = service.create("Unsafe JD", "A sufficiently long pasted job description.")["run_id"]
    service.analyze(run_id)
    service.approve_strategy(run_id)
    service.compile(run_id)
    assert service.get(run_id)["status"] == "FAILED"
    assert provider.calls.count("ResumePatch") == 2
    assert "HiringEvaluation" not in provider.calls


def test_stale_active_run_is_marked_interrupted_and_can_retry(tmp_path):
    service = make_service(tmp_path)
    run_id = service.create("Retry JD", "A sufficiently long pasted job description.")["run_id"]
    restarted = make_service(tmp_path)
    assert restarted.get(run_id)["status"] == "INTERRUPTED"
    assert restarted.retry_analysis(run_id)["status"] == "ANALYZING"


def test_company_is_auto_filled_from_job_profile_when_not_provided(tmp_path):
    service = make_service(tmp_path)
    run_id = service.create("Google AI Agent", "A sufficiently long pasted job description.")["run_id"]
    assert service.get(run_id)["company"] is None
    service.analyze(run_id)
    assert service.get(run_id)["company"] == "Google"


def test_explicit_company_is_not_overwritten_by_auto_fill(tmp_path):
    service = make_service(tmp_path)
    run_id = service.create(
        "Google AI Agent", "A sufficiently long pasted job description.", company="Custom Co"
    )["run_id"]
    service.analyze(run_id)
    assert service.get(run_id)["company"] == "Custom Co"


def test_update_notes(tmp_path):
    service = make_service(tmp_path)
    run_id = service.create("Google AI Agent", "A sufficiently long pasted job description.")["run_id"]
    assert service.update_notes(run_id, "跟进一下内推")["notes"] == "跟进一下内推"
    assert service.get(run_id)["notes"] == "跟进一下内推"


def test_list_runs_pagination_and_sort_order(tmp_path):
    service = make_service(tmp_path)
    ids = [
        service.create(f"JD {i}", "A sufficiently long pasted job description.")["run_id"]
        for i in range(3)
    ]

    all_runs = service.list_runs()
    assert all_runs["total"] == 3
    assert [item["run_id"] for item in all_runs["items"]] == list(reversed(ids))

    first_page = service.list_runs(page=1, page_size=2)
    assert first_page["total"] == 3
    assert len(first_page["items"]) == 2
    second_page = service.list_runs(page=2, page_size=2)
    assert len(second_page["items"]) == 1
    assert {item["run_id"] for item in first_page["items"]} | {
        item["run_id"] for item in second_page["items"]
    } == set(ids)


def test_get_events_returns_run_history(tmp_path):
    service = make_service(tmp_path)
    run_id = service.create("Google AI Agent", "A sufficiently long pasted job description.")["run_id"]
    events = service.get_events(run_id)
    assert events[0]["status"] == "INIT"
    assert any(event["status"] == "ANALYZING" for event in events)


def test_manual_edit_accumulates_diff_with_editor_patch(tmp_path):
    service = make_service(tmp_path)
    run_id = service.create("Google AI Agent", "A sufficiently long pasted job description.")["run_id"]
    service.analyze(run_id)
    service.approve_strategy(run_id)
    service.compile(run_id)
    assert service.get(run_id)["status"] == "WAITING_FINAL_APPROVAL"

    diff_before = service.get_diff(run_id)
    assert [item["path"] for item in diff_before] == ["/sections/introduction/body"]

    patch = ResumePatch.model_validate(
        {
            "operations": [
                {
                    "op": "replace",
                    "path": "/sections/skills/rows/ai_agent_development/items",
                    "supported_by": ["fact_introduction_body"],
                    "reason": "manual tweak",
                    "value": {"zh": "手动新增技能描述", "en": "Manually added skill text"},
                }
            ]
        }
    )
    service.manual_edit(run_id, patch)

    diff_after = service.get_diff(run_id)
    paths = {item["path"] for item in diff_after}
    assert paths == {
        "/sections/introduction/body",
        "/sections/skills/rows/ai_agent_development/items",
    }


def test_restore_original_clears_accumulated_operations(tmp_path):
    service = make_service(tmp_path)
    run_id = service.create("Google AI Agent", "A sufficiently long pasted job description.")["run_id"]
    service.analyze(run_id)
    service.approve_strategy(run_id)
    service.compile(run_id)

    service.restore_original(run_id)
    assert service.get_diff(run_id) == []
    all_ops_path = service.resolve_run(run_id) / "all_operations.json"
    assert all_ops_path.exists()
    assert json.loads(all_ops_path.read_text(encoding="utf-8")) == []


def test_approve_final_and_reject_final_update_stage(tmp_path):
    approve_service = make_service(tmp_path)
    run_id = approve_service.create(
        "Google AI Agent", "A sufficiently long pasted job description."
    )["run_id"]
    approve_service.analyze(run_id)
    approve_service.approve_strategy(run_id)
    approve_service.compile(run_id)
    approved = approve_service.approve_final(run_id)
    assert approved["stage"] != "Human Gate ②：等待最终确认"

    reject_service = make_service(tmp_path)
    run_id_2 = reject_service.create(
        "Google AI Agent 2", "A sufficiently long pasted job description."
    )["run_id"]
    reject_service.analyze(run_id_2)
    reject_service.approve_strategy(run_id_2)
    reject_service.compile(run_id_2)
    rejected = reject_service.reject_final(run_id_2)
    assert rejected["stage"] != "Human Gate ②：等待最终确认"


def test_langsmith_trace_url_reflects_settings(tmp_path):
    settings = Settings(api_key="fake", langsmith_project_url="https://smith.langchain.com/o/x/projects/p/y")
    service = WorkflowService(HappyProvider(), settings, runs_root=tmp_path)
    run_id = service.create("Google AI Agent", "A sufficiently long pasted job description.")["run_id"]
    assert service.get(run_id)["langsmith_trace_url"] == "https://smith.langchain.com/o/x/projects/p/y"

    default_service = make_service(tmp_path)
    run_id_2 = default_service.create("Google AI Agent 2", "A sufficiently long pasted job description.")["run_id"]
    assert default_service.get(run_id_2)["langsmith_trace_url"] is None
